# LOKI v2 — Sarvam Voice Assistant

A starter web-based voice assistant with a futuristic LOKI interface. Sarvam handles speech-to-text, chat, and text-to-speech. The API key stays on the Python server and is never sent to the browser.

## Included
- LOKI v2 responsive web UI
- Text chat through Sarvam Chat Completions (`sarvam-105b`)
- Voice input through Saaras speech-to-text (`saaras:v3`)
- Spoken response through Bulbul text-to-speech (`bulbul:v3`)
- `.env.example` and `.gitignore` to keep secrets out of Git
- Microphone permission and keyboard fallback

## Important
This is a starter project, not a full operating-system assistant. It does not yet control Android apps, wake on a background phrase, make phone calls, or run while the browser is closed. Browser microphone recording requires a supported browser and a secure context (localhost is allowed).

## Run locally
Use Python 3.10 or newer if possible.

1. Extract the ZIP.
2. Open the project folder in a terminal.
3. Create a virtual environment (optional but recommended):
   - Windows: `python -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install packages: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`.
6. Open `.env` and set `SARVAM_API_KEY=your_new_key_here`.
7. Start: `python app.py`
8. Open `http://127.0.0.1:5000`.

Do not paste your API key into chat or commit `.env` to GitHub. If a key was shared in a chat or committed, rotate it in the Sarvam dashboard.

## API notes
The implementation calls Sarvam REST endpoints from the server:
- `POST /speech-to-text`
- `POST /chat/completions`
- `POST /text-to-speech`

If your Sarvam account does not have access to a model, check the official Sarvam dashboard/docs and update the model value. Error details appear in the session console.

## Suggested GitHub files
Upload the project contents to the root of `Karthik12356/Loki_Ai` (not the parent folder itself). Never upload `.env`; upload `.env.example` only.
