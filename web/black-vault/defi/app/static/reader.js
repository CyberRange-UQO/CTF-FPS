"use strict";

const form = document.querySelector("#reader-form");
const reference = document.querySelector("#file");
const panel = document.querySelector("#response-panel");
const feedback = document.querySelector("#reader-feedback");
const content = document.querySelector("#document-content");
const state = document.querySelector("#response-state");
const address = document.querySelector("#request-url");
const metadata = document.querySelector("#document-meta");
let pending = null;

async function readDocument() {
  if (pending) pending.abort();
  const controller = new AbortController();
  pending = controller;
  const params = new URLSearchParams({ file: reference.value });
  const endpoint = `${form.dataset.endpoint}?${params.toString()}`;
  address.href = endpoint;
  address.textContent = endpoint;
  history.replaceState(null, "", `/reader?${params.toString()}`);
  panel.dataset.state = "loading";
  panel.setAttribute("aria-busy", "true");
  state.textContent = "LECTURE";
  content.textContent = "";
  metadata.textContent = "LECTURE SEULE";
  feedback.textContent = "Consultation du document…";
  try {
    const response = await fetch(endpoint, {
      credentials: "same-origin", cache: "no-store", signal: controller.signal,
    });
    const result = await response.json();
    if (!response.ok) {
      panel.dataset.state = "error";
      state.textContent = `${response.status} / ${result.error}`;
      feedback.textContent = result.message;
      return;
    }
    panel.dataset.state = "success";
    state.textContent = "200 / DOCUMENT LU";
    feedback.textContent = `Archive ${result.archive_ref} · ${result.reference}`;
    // Document bytes are always text, never executable markup.
    content.textContent = result.content;
    metadata.textContent = `${result.format.toUpperCase()} / ${result.bytes} OCTETS`;
  } catch (error) {
    if (error.name === "AbortError") return;
    panel.dataset.state = "error";
    state.textContent = "LECTURE INTERROMPUE";
    feedback.textContent = "Le lecteur est indisponible. Vérifiez votre session et réessayez.";
  } finally {
    if (pending === controller) {
      panel.setAttribute("aria-busy", "false");
      pending = null;
    }
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  readDocument();
});
readDocument();
