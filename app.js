const $ = (id) => document.getElementById(id);
const voiceBtn = $("voiceBtn");
const voiceBtnText = $("voiceBtnText");
const hint = $("hint");
const core = $("core");
const coreCaption = $("coreCaption");
const messages = $("messages");
const chatForm = $("chatForm");
const messageInput = $("messageInput");
const stopBtn = $("stopBtn");
let recorder = null;
let chunks = [];
let recording = false;
let currentAudio = null;

function setMode(mode, message) {
  core.classList.toggle("listening", mode === "listening");
  core.classList.toggle("thinking", mode === "thinking");
  coreCaption.textContent = ({idle:"SYSTEM STANDBY", listening:"LISTENING", thinking:"PROCESSING NEURAL INPUT", speaking:"VOICE OUTPUT"})[mode] || "SYSTEM STANDBY";
  hint.textContent = message || "";
  voiceBtnText.textContent = mode === "listening" ? "STOP & PROCESS" : "ENGAGE LOKI";
}
function addMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const tag = document.createElement("span");
  tag.className = "msg-tag";
  tag.textContent = role === "user" ? "YOU" : role === "error" ? "SYSTEM" : "LOKI";
  const p = document.createElement("p");
  p.textContent = text;
  wrap.append(tag, p);
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
}
async function checkStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    $("statusDot").classList.toggle("ready", data.ready);
    $("statusText").textContent = data.ready ? "API READY" : "KEY REQUIRED";
    if (!data.ready) hint.textContent = "Add your Sarvam key to .env on the server, then restart LOKI.";
  } catch {
    $("statusText").textContent = "SERVER OFFLINE";
  }
}
async function sendText(text) {
  addMessage("user", text);
  setMode("thinking", "LOKI is thinking…");
  try {
    const res = await fetch("/api/chat", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({message:text})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed.");
    addMessage("system", data.reply);
    setMode("idle", "Response received. Tap to speak again.");
  } catch (e) {
    addMessage("error", e.message);
    setMode("idle", "Check the server and your Sarvam API key.");
  }
}
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = "";
  await sendText(text);
});
$("keyboardBtn").addEventListener("click", () => {
  messageInput.focus();
  messageInput.scrollIntoView({behavior:"smooth",block:"center"});
});
async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    hint.textContent = "This browser does not support microphone recording. Use the type-message box.";
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    chunks = [];
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "";
    recorder = new MediaRecorder(stream, mime ? {mimeType:mime} : undefined);
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      recording = false;
      const blob = new Blob(chunks, {type:recorder.mimeType || "audio/webm"});
      await processVoice(blob);
    };
    recorder.start();
    recording = true;
    setMode("listening", "Listening… tap STOP & PROCESS when you finish.");
  } catch (e) {
    setMode("idle", "Microphone permission was denied or unavailable. You can type instead.");
  }
}
async function processVoice(blob) {
  setMode("thinking", "Transcribing, thinking, and preparing voice output…");
  const form = new FormData();
  const ext = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
  form.append("audio", blob, `loki-recording.${ext}`);
  try {
    const res = await fetch("/api/voice", {method:"POST",body:form});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Voice request failed.");
    addMessage("user", data.transcript);
    addMessage("system", data.reply);
    if (data.audio_url) {
      if (currentAudio) currentAudio.pause();
      currentAudio = new Audio(data.audio_url);
      stopBtn.disabled = false;
      setMode("speaking", "LOKI is speaking…");
      currentAudio.onended = () => { stopBtn.disabled = true; setMode("idle", "Tap to speak again."); };
      currentAudio.onerror = () => { stopBtn.disabled = true; setMode("idle", "Reply received, but audio playback failed."); };
      await currentAudio.play();
    } else setMode("idle", "Reply received.");
  } catch (e) {
    addMessage("error", e.message);
    setMode("idle", "Voice processing failed. Check your key, API access, and server log.");
  }
}
voiceBtn.addEventListener("click", async () => {
  if (recording && recorder) {
    voiceBtn.disabled = true;
    recorder.stop();
    voiceBtn.disabled = false;
  } else {
    await startRecording();
  }
});
stopBtn.addEventListener("click", () => {
  if (currentAudio) currentAudio.pause();
  stopBtn.disabled = true;
  setMode("idle", "Audio stopped.");
});
function tick() { $("clock").textContent = new Date().toLocaleTimeString([], {hour12:false}); }
tick(); setInterval(tick,1000); checkStatus();