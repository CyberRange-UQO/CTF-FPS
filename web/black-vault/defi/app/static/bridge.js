"use strict";

const form = document.querySelector("#bridge-form");
const terminal = document.querySelector("#bridge-terminal");
const transcript = document.querySelector("#transcript");
const choices = document.querySelector("#bridge-choices");
const feedback = document.querySelector("#bridge-feedback");
const state = document.querySelector("#bridge-state");
const channel = document.querySelector("#channel-reading-state");
const attestation = document.querySelector("#attestation");
const controls = document.querySelector("#transmission-controls");
const reveal = document.querySelector("#reveal-messages");
const pause = document.querySelector("#pause-reading");
const replay = document.querySelector("#replay-transcript");
const immediate = document.querySelector("#immediate-reading");
const traceLink = document.querySelector("#contact-trace-link");
const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
const csrf = document.querySelector('meta[name="csrf-token"]').content;
let sessionId = null;
let serverState = null;
let busy = false;
let history = [];
let pending = [];
let timer = null;
let paused = false;
let replaying = false;
immediate.checked = motion.matches;

function updateControls() {
  reveal.disabled = pending.length === 0;
  pause.disabled = pending.length === 0 || immediate.checked;
  pause.textContent = paused ? "Reprendre la lecture" : "Suspendre la lecture";
  pause.setAttribute("aria-pressed", String(paused));
  replay.disabled = busy || history.length === 0;
}

function setBusy(value) {
  busy = value;
  // Network work only: narrative pacing never makes the API controls busy.
  terminal.setAttribute("aria-busy", String(value));
  for (const button of [...form.querySelectorAll("button"), ...choices.querySelectorAll("button")]) {
    button.disabled = value;
  }
  updateControls();
}

async function send(endpoint, payload) {
  const response = await fetch(endpoint, {
    method: "POST", credentials: "same-origin", cache: "no-store",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.message || "Le canal est indisponible.");
  return result;
}

function appendMessage(message) {
  const line = document.createElement("article");
  line.className = message.important ? "message message-important" : "message";
  line.dataset.speaker = message.speaker;
  const label = document.createElement("strong");
  label.textContent = message.speaker;
  const body = document.createElement("p");
  body.textContent = message.text;
  line.append(label, body);
  transcript.append(line);
  if (message.closing) channel.textContent = "SIGNAL LOST · TRACE CONSERVÉE";
  else if (serverState === "connected" && !replaying && message.speaker === "MIRA") {
    channel.textContent = "TRANSMISSION ACTIVE";
  }
}

function stopTimer() {
  clearTimeout(timer);
  timer = null;
}

function readingFinished() {
  const wasReplaying = replaying;
  replaying = false;
  if (serverState === "completed") {
    channel.textContent = "SIGNAL LOST · CONTACT ATTESTED";
    // Reward wording only once the last words and the cut-off have been read.
    // A replay of an already-received transcript must not re-announce it.
    if (!wasReplaying) feedback.textContent = "Canal interrompu. Attestation de contact disponible.";
  }
  updateControls();
}

function revealAvailable() {
  stopTimer();
  // This queue contains only messages already returned by the server.
  for (const message of pending.splice(0)) appendMessage(message);
  readingFinished();
}

function readNext() {
  stopTimer();
  if (paused || document.hidden) return;
  if (immediate.checked) { revealAvailable(); return; }
  const message = pending.shift();
  if (!message) { readingFinished(); return; }
  appendMessage(message);
  updateControls();
  if (!pending.length) { readingFinished(); return; }
  const words = message.text.split(/\s+/).length;
  const silence = message.text.startsWith("…") || message.text === "D'accord.";
  timer = setTimeout(readNext, Math.min(6500, Math.max(silence ? 2600 : 1400, words * 190)));
}

function showResult(result) {
  sessionId = result.session_id;
  serverState = result.state;
  state.textContent = serverState === "completed" ? "CONTACT ATTESTED" : "CHANNEL ESTABLISHED";
  state.className = "badge badge-active";
  terminal.dataset.state = serverState;
  channel.textContent = serverState === "completed" ? "CANAL INTERROMPU / LECTURE DE LA TRACE" : "CHANNEL ESTABLISHED";
  controls.hidden = false;
  const lastMira = result.messages.map((message) => message.speaker).lastIndexOf("MIRA");
  const batch = result.messages.map((message, index) => ({
    speaker: message.speaker, text: message.text,
    important: serverState === "completed" && index === lastMira,
    closing: serverState === "completed" && message.speaker === "SYSTÈME",
  }));
  history.push(...batch);
  pending.push(...batch);
  replaying = false;
  choices.replaceChildren();
  for (const choice of result.choices) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button button-primary";
    button.textContent = choice.text;
    button.disabled = busy;
    button.addEventListener("click", () => advance(choice));
    choices.append(button);
  }
  if (result.attestation) {
    const trace = result.attestation;
    document.querySelector("#attestation-meta").textContent = `${trace.id} · ${trace.status} · ${trace.issued_at}`;
    document.querySelector("#attestation-refs").textContent = `Archive : ${trace.archive_ref} · Allocation : ${trace.allocation_ref}`;
    document.querySelector("#attestation-proof").textContent = trace.proof;
    document.querySelector("#attestation-link").href = `/api/bridge/${encodeURIComponent(sessionId)}`;
    // Available immediately on the real completed response, never behind playback.
    attestation.hidden = false;
    traceLink.hidden = false;
    // Discreet while the last words are still being read; the cut-off wording
    // is set by readingFinished(). Access to the attestation/flag is not gated.
    feedback.textContent = "Trace de contact conservée.";
  } else {
    feedback.textContent = "Canal établi. Les réponses sont disponibles sans attendre la fin de la lecture.";
  }
  updateControls();
  readNext();
}

async function advance(choice) {
  if (busy || !sessionId) return;
  revealAvailable();
  setBusy(true);
  let advanced = false;
  try {
    const result = await send("/api/bridge/advance", { session_id: sessionId, response_id: choice.id });
    const message = { speaker: "STATIC", text: choice.text };
    history.push(message);
    appendMessage(message);
    showResult(result);
    advanced = true;
  } catch (error) {
    feedback.textContent = error.message;
  } finally {
    setBusy(false);
    if (advanced) (choices.querySelector("button") || transcript).focus({ preventScroll: true });
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  stopTimer();
  setBusy(true);
  let opened = false;
  try {
    const payload = Object.fromEntries(new FormData(form));
    const result = await send("/api/bridge/open", payload);
    history = [];
    pending = [];
    paused = false;
    replaying = false;
    transcript.replaceChildren();
    attestation.hidden = true;
    attestation.open = false;
    traceLink.hidden = true;
    document.querySelector("#attestation-proof").textContent = "";
    document.querySelector("#attestation-meta").textContent = "";
    document.querySelector("#attestation-refs").textContent = "";
    document.querySelector("#attestation-link").removeAttribute("href");
    showResult(result);
    opened = true;
  } catch (error) {
    feedback.textContent = error.message;
    // A rejected reopening does not erase the trace already received.
    readNext();
  } finally {
    setBusy(false);
    if (opened) (choices.querySelector("button") || transcript).focus({ preventScroll: true });
  }
});

reveal.addEventListener("click", revealAvailable);
pause.addEventListener("click", () => {
  paused = !paused;
  stopTimer();
  updateControls();
  if (!paused) readNext();
});
immediate.addEventListener("change", () => {
  if (immediate.checked) { paused = false; revealAvailable(); }
  else updateControls();
});
replay.addEventListener("click", () => {
  if (busy || !history.length) return;
  stopTimer();
  transcript.replaceChildren();
  pending = [...history];
  paused = false;
  replaying = true;
  channel.textContent = "RELECTURE / MESSAGES REÇUS";
  readNext();
  transcript.focus({ preventScroll: true });
});
traceLink.addEventListener("click", (event) => {
  event.preventDefault();
  attestation.open = true;
  attestation.querySelector("summary").focus();
});
motion.addEventListener("change", () => {
  if (motion.matches) { immediate.checked = true; paused = false; revealAvailable(); }
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopTimer();
  else if (!busy) readNext();
});
window.addEventListener("pagehide", stopTimer);
