import base64
import os
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
SARVAM_BASE = "https://api.sarvam.ai"


def sarvam_headers(json_body=True):
    if not SARVAM_API_KEY:
        raise RuntimeError(
            "SARVAM_API_KEY is missing. Copy .env.example to .env and add your key."
        )
    headers = {"api-subscription-key": SARVAM_API_KEY}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def ask_loki(user_text):
    response = requests.post(
        f"{SARVAM_BASE}/chat/completions",
        headers=sarvam_headers(),
        json={
            "model": "sarvam-105b",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are LOKI v2, a helpful, friendly, concise voice assistant. "
                        "Call the user 'bro' occasionally, not in every sentence. "
                        "Be honest about limitations. Do not claim to control device settings "
                        "or apps unless an actual integration is implemented."
                    ),
                },
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.5,
            "max_tokens": 700,
        },
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"Sarvam chat API error {response.status_code}: {response.text[:500]}")
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"Unexpected chat response from Sarvam: {str(data)[:500]}")
    if not content:
        return "I couldn't form a reply that time. Try asking me again."
    return content


def speech_to_text(audio_path, mime_type):
    # Saaras v3 supports multiple Indian languages; auto language detection is used here.
    with open(audio_path, "rb") as audio_file:
        response = requests.post(
            f"{SARVAM_BASE}/speech-to-text",
            headers={"api-subscription-key": SARVAM_API_KEY},
            files={"file": (Path(audio_path).name, audio_file, mime_type)},
            data={"model": "saaras:v3", "mode": "transcribe", "language_code": "unknown"},
            timeout=120,
        )
    if not response.ok:
        raise RuntimeError(f"Sarvam speech-to-text error {response.status_code}: {response.text[:500]}")
    data = response.json()
    transcript = data.get("transcript", "")
    if not transcript:
        raise RuntimeError("Sarvam did not return a transcript. Try recording again.")
    return transcript


def text_to_speech(text, language_code="en-IN"):
    # Bulbul v3 is the stable option; change to bulbul:v4-flash if enabled for your key.
    response = requests.post(
        f"{SARVAM_BASE}/text-to-speech",
        headers=sarvam_headers(),
        json={
            "text": text[:2500],
            "language_code": language_code,
            "speaker": "shubh",
            "model": "bulbul:v3",
            "speech_sample_rate": 22050,
            "output_audio_codec": "mp3",
        },
        timeout=90,
    )
    if not response.ok:
        raise RuntimeError(f"Sarvam text-to-speech error {response.status_code}: {response.text[:500]}")
    data = response.json()
    audios = data.get("audios") or []
    if not audios:
        raise RuntimeError("Sarvam did not return audio.")
    audio_bytes = base64.b64decode(audios[0])
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    try:
        temp.write(audio_bytes)
        temp.close()
        return temp.name
    except Exception:
        temp.close()
        raise


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify({"ready": bool(SARVAM_API_KEY), "assistant": "LOKI v2"})


@app.post("/api/chat")
def chat():
    try:
        body = request.get_json(silent=True) or {}
        user_text = str(body.get("message", "")).strip()
        if not user_text:
            return jsonify({"error": "Type a message first."}), 400
        reply = ask_loki(user_text)
        return jsonify({"reply": reply})
    except requests.Timeout:
        return jsonify({"error": "Sarvam took too long to respond. Try again."}), 504
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/voice")
def voice():
    audio_path = None
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No recording received. Allow microphone access and try again."}), 400
        audio = request.files["audio"]
        if not audio.filename:
            return jsonify({"error": "The recording was empty."}), 400

        suffix = Path(audio.filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            audio_path = temp.name
            audio.save(audio_path)

        mime_type = audio.mimetype or "audio/webm"
        transcript = speech_to_text(audio_path, mime_type)
        reply = ask_loki(transcript)
        audio_file = text_to_speech(reply, request.form.get("language_code", "en-IN"))

        # Return transcript + reply text, with audio in a separate URL for browser playback.
        audio_name = Path(audio_file).name
        app.config.setdefault("audio_files", {})[audio_name] = audio_file
        return jsonify({
            "transcript": transcript,
            "reply": reply,
            "audio_url": f"/api/audio/{audio_name}"
        })
    except requests.Timeout:
        return jsonify({"error": "Voice request timed out. Try a shorter recording."}), 504
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


@app.get("/api/audio/<audio_name>")
def audio(audio_name):
    audio_path = app.config.get("audio_files", {}).get(audio_name)
    if not audio_path or not os.path.exists(audio_path):
        return jsonify({"error": "Audio has expired. Ask LOKI to speak again."}), 404
    return send_file(audio_path, mimetype="audio/mpeg", as_attachment=False)


if __name__ == "__main__":
    # Local development only. Do not expose this development server directly to the internet.
    app.run(host="127.0.0.1", port=5000, debug=True)
