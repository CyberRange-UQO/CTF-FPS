/* Remote content is data: all rendering uses textContent, never innerHTML. */
"use strict";

const form = document.querySelector("#preview-form");
const input = document.querySelector("#resource-url");
const submit = document.querySelector("#preview-submit");
const result = document.querySelector("#preview-result");
const feedback = document.querySelector("#request-feedback");
const state = document.querySelector("#response-state");
const content = document.querySelector("#response-content");
const body = document.querySelector("#response-body");
const navigation = document.querySelector("#resource-navigation");
const pathsContainer = document.querySelector("#resource-paths");
const copyButton = document.querySelector("#copy-body");
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const help = document.querySelector("#response-help");
const validationHelp = document.querySelector("#validation-help");
const sessionLogin = document.querySelector("#session-login");
let running = false;

function resourcePaths(data) {
  const found = new Set();
  function walk(value, depth) {
    if (depth > 12 || found.size >= 24) return;
    if (typeof value === "string" && /^\/(?!\/)[A-Za-z0-9_./-]*$/.test(value)) {
      found.add(value);
    } else if (Array.isArray(value)) {
      value.forEach((item) => walk(item, depth + 1));
    } else if (value && typeof value === "object") {
      Object.values(value).forEach((item) => walk(item, depth + 1));
    }
  }
  walk(data, 0);
  return found;
}

function setBusy(busy) {
  running = busy;
  submit.disabled = busy;
  input.readOnly = busy;
  document.querySelector("#load-example").disabled = busy;
  result.setAttribute("aria-busy", String(busy));
  submit.textContent = busy ? "Consultation…" : "Consulter →";
}

async function consult() {
  if (running) return;
  setBusy(true);
  content.hidden = true;
  help.hidden = true;
  validationHelp.hidden = true;
  sessionLogin.hidden = true;
  navigation.hidden = true;
  pathsContainer.replaceChildren();
  body.textContent = "";
  result.dataset.state = "loading";
  state.textContent = "EN COURS";
  feedback.textContent = "Requête HTTP en cours depuis MIRROR GATE…";
  copyButton.textContent = "Copier le contenu";
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      credentials: "same-origin",
      body: JSON.stringify({ url: input.value.trim() }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      result.dataset.state = "error";
      state.textContent = "ÉCHEC DE CONSULTATION";
      feedback.textContent = `${data.message || "La demande n'a pas pu être traitée."} (${data.error || response.status})`;
      if (data.error === "DESTINATION_NOT_APPROVED") {
        state.textContent = "SOURCE NON APPROUVÉE";
        help.hidden = false;
        validationHelp.hidden = false;
      } else if (data.error === "SESSION_REQUIRED") {
        state.textContent = "CONNEXION REQUISE";
        help.hidden = false;
        sessionLogin.hidden = false;
      }
      return;
    }
    let parsed = null;
    let displayed = data.body;
    if (!data.truncated && data.content_type.toLowerCase().includes("json")) {
      try {
        parsed = JSON.parse(data.body);
        displayed = JSON.stringify(parsed, null, 2);
      } catch (_) { /* Show the exact text if the source returns malformed JSON. */ }
    }
    const statusGroup = Math.floor(data.upstream_status / 100);
    result.dataset.state = statusGroup === 2 ? "success" : statusGroup === 3 ? "redirect" : "upstream-error";
    result.dataset.classification = data.classification || "";
    state.textContent = `HTTP ${data.upstream_status}`;
    feedback.textContent = statusGroup === 3
      ? "Réponse de redirection reçue. La redirection n'a pas été suivie."
      : "Réponse HTTP reçue de la source. Le statut ci-dessous est celui du service distant.";
    document.querySelector("#upstream-status").textContent = String(data.upstream_status);
    document.querySelector("#content-type").textContent = data.content_type;
    document.querySelector("#duration").textContent = `${data.duration_ms} ms`;
    document.querySelector("#classification").textContent = data.classification || "NON FOURNIE";
    document.querySelector("#requested-url").textContent = data.requested_url;
    document.querySelector("#truncation-warning").hidden = !data.truncated;
    body.textContent = displayed;
    content.hidden = false;
    if (parsed && statusGroup === 2) {
      const base = new URL(data.requested_url);
      for (const path of resourcePaths(parsed)) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "path-button";
        button.textContent = `${path} →`;
        button.addEventListener("click", () => {
          if (running) return;
          const next = new URL(path, base);
          if (next.origin !== base.origin) return;
          // Keep the operator's accepted URL representation for each consultation.
          // No browser request is made to this address.
          next.username = base.username;
          next.password = base.password;
          input.value = next.href;
          consult();
        });
        pathsContainer.append(button);
      }
      navigation.hidden = pathsContainer.childElementCount === 0;
    }
  } catch (error) {
    result.dataset.state = "error";
    state.textContent = "PORTAIL INJOIGNABLE";
    feedback.textContent = error.name === "AbortError"
      ? "Le portail n'a pas répondu à temps. Aucune réponse distante n'a pu être affichée."
      : "Impossible de recevoir la réponse du portail. Vérifiez votre connexion et réessayez.";
  } finally {
    window.clearTimeout(timeout);
    setBusy(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  consult();
});
document.querySelector("#load-example").addEventListener("click", () => {
  input.value = "http://mirror-catalog:9080/public/bulletin";
  input.focus();
});
copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(body.textContent);
    copyButton.textContent = "Contenu copié ✓";
  } catch (_) {
    copyButton.textContent = "Sélectionnez le texte pour le copier";
    body.focus();
    const range = document.createRange();
    range.selectNodeContents(body);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }
});
