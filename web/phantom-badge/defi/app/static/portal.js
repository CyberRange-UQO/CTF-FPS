"use strict";
// The badge is kept only in memory and sent on real same-origin API requests.
// No client-side decision grants access or unlocks confidential data.
async function presentBadge(endpoint) {
  const badgeResponse = await fetch("/api/session/badge", {credentials: "same-origin", cache: "no-store"});
  if (!badgeResponse.ok) throw new Error("Votre session a expiré. Reconnectez-vous au portail.");
  const {badge} = await badgeResponse.json();
  const response = await fetch(endpoint, {
    credentials: "same-origin", cache: "no-store", headers: {"Authorization": `Bearer ${badge}`}
  });
  return {response, data: await response.json()};
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function result(box, label, text, state) {
  box.className = `result-box ${state || ""}`;
  box.replaceChildren(element("span", label, "eyebrow"), element("p", text));
}
function renderReport(report) {
  const container = document.getElementById("report-container");
  const section = element("section", undefined, "panel report");
  const heading = element("div", undefined, "report-top");
  const title = element("div");
  title.append(element("span", "DOSSIER CONFIDENTIEL / CONSULTATION AUTORISÉE", "eyebrow accent"), element("h2", report.title), element("span", report.classification, "mono"));
  heading.append(title, element("span", report.status, "badge badge-pink"));
  const meta = element("dl", undefined, "report-meta");
  for (const [label, value] of [["Déclarante", report.declarant], ["Affectation", report.assignment]]) {
    const field = element("div"); field.append(element("dt", label), element("dd", value)); meta.append(field);
  }
  const timeline = element("div", undefined, "timeline");
  for (const event of report.events) {
    const entry = element("article");
    entry.append(element("span", event.date, "eyebrow accent"), element("h3", event.label), element("p", event.detail));
    timeline.append(entry);
  }
  const proof = element("div", undefined, "proof");
  proof.append(element("span", "IDENTIFIANT DE PREUVE", "eyebrow accent"), element("code", report.proof_id));
  section.append(heading, meta, timeline, proof); container.replaceChildren(section);
}
function scanBadge(zone) {
  // Restart only this finite scan if a new attempt arrives before it has finished.
  if (zone.classList.contains("is-scanning")) {
    zone.classList.remove("is-scanning");
    void zone.offsetWidth;
  }
  zone.classList.add("is-scanning");
}
const verify = document.getElementById("verify-badge");
if (verify) verify.addEventListener("click", async () => {
  const box = document.getElementById("identity-result"); verify.disabled = true;
  const panel = verify.closest(".verification-panel"); panel.dataset.state = "processing";
  result(box, "VÉRIFICATION EN COURS", "Connexion au service d'identité…");
  try {
    const {response, data} = await presentBadge("/api/identity/me");
    if (response.ok) {
      panel.dataset.state = "granted";
      result(box, "BADGE AUTHENTIFIÉ / ACTIVE", `${data.sub} · ${data.division} / ${data.clearance}`, "granted");
    } else {
      panel.dataset.state = "denied";
      result(box, "BADGE REFUSÉ", `Le service d'identité ne peut pas valider ce badge. Référence : ${data.reason || data.status}.`, "denied");
    }
  } catch (error) {
    panel.dataset.state = "denied";
    result(box, "SERVICE INDISPONIBLE", error.message, "denied");
  }
  finally { verify.disabled = false; }
});
const present = document.getElementById("present-badge");
const scanZone = document.querySelector(".badge-scan-zone");
if (scanZone) scanZone.addEventListener("animationend", (event) => {
  if (event.animationName === "cipher-badge-scan") scanZone.classList.remove("is-scanning");
});
if (present) present.addEventListener("click", async () => {
  const box = document.getElementById("cipher-result"); present.disabled = true;
  const terminal = present.closest(".terminal"); terminal.dataset.state = "processing";
  scanBadge(scanZone);
  document.getElementById("report-container").replaceChildren();
  document.getElementById("presented-badge").textContent = "Présentation en cours";
  result(box, "CONTRÔLE EN COURS", "Présentation au terminal CIPHER…");
  try {
    const {response, data} = await presentBadge("/api/legacy/cipher/access");
    document.getElementById("presented-badge").textContent = data.badge_presented || "Badge non validé";
    if (response.ok && data.status === "ACCESS_GRANTED") {
      terminal.dataset.state = "granted";
      result(box, "ACCÈS AUTORISÉ", "Habilitation acceptée. Le dossier d'incident est disponible pour consultation.", "granted");
      renderReport(data.report);
    } else if (response.status === 403) {
      terminal.dataset.state = "denied";
      result(box, "ACCÈS REFUSÉ", "Votre badge ne satisfait pas la politique d'habilitation de cette zone. Contactez votre responsable de périmètre si votre affectation a changé.", "denied");
    } else {
      terminal.dataset.state = "denied";
      result(box, "BADGE REFUSÉ", `Le terminal ne peut pas accepter ce badge. Référence : ${data.reason || data.status}.`, "denied");
    }
  } catch (error) {
    terminal.dataset.state = "denied";
    result(box, "SERVICE INDISPONIBLE", error.message, "denied");
  }
  finally { present.disabled = false; }
});
