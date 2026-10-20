"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const caseId = "CASE-SIL-2147-07";
  const eventsPath = `/api/cases/${caseId}/events`;
  let readToken = "";
  let unlocked = false;
  let authorityDeadline = 0;
  let expiryTimer = null;
  let transitionTimer = null;
  let authorityController = null;
  let events = [];
  let envelope = null;
  let accessRevision = 0;
  const selected = new Set();
  const workspaceIds = ["register", "proof", "disclosure", "receipts", "contracts"];
  let activeWorkspace = workspaceIds.includes(location.hash.slice(1)) ? location.hash.slice(1) : "register";

  function showWorkspace(id, { focus = false } = {}) {
    if (!workspaceIds.includes(id)) return;
    activeWorkspace = id;
    workspaceIds.forEach((view) => { byId(view).hidden = view !== id; });
    document.querySelectorAll('.workspace-nav [data-workspace]').forEach((link) => {
      if (link.dataset.workspace === id) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    if (focus && unlocked) byId(`${id}-title`).focus();
  }

  document.querySelectorAll('[data-workspace]').forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      if (!hasReadAuthority()) return;
      history.pushState(null, "", `#${link.dataset.workspace}`);
      showWorkspace(link.dataset.workspace, { focus: true });
    });
  });
  const restoreWorkspace = () => {
    const id = location.hash.slice(1);
    if (unlocked && workspaceIds.includes(id)) showWorkspace(id, { focus: true });
  };
  window.addEventListener("popstate", restoreWorkspace);
  window.addEventListener("hashchange", restoreWorkspace);
  showWorkspace(activeWorkspace);

  const display = (id, message, state = "") => {
    byId(id).textContent = message;
    byId(id).dataset.state = state;
  };
  const showJSON = (id, value) => { byId(id).textContent = JSON.stringify(value, null, 2); };
  const tokenValue = (input) => input.value.trim().replace(/^Bearer\s+/i, "");
  const describeError = (error) => `${error.code || "NETWORK_ERROR"} — ${error.message}`;

  async function api(path, { token = "", body, method = "GET", signal } = {}) {
    const headers = { "Accept": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let response;
    try {
      response = await fetch(path, {
        method, headers, body, signal, credentials: "omit", cache: "no-store", redirect: "error",
      });
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw { code: "NETWORK_ERROR", message: "L'autorité est inaccessible. Réessayez la requête." };
    }
    let data;
    try { data = await response.json(); }
    catch { throw { code: "HTTP_ERROR", message: `Réponse HTTP ${response.status} illisible.` }; }
    if (!response.ok) throw { code: data.error, message: data.message, status: response.status };
    return data;
  }

  function addPair(target, key, value) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = key;
    dd.textContent = value;
    target.append(dt, dd);
  }

  const gatewayStates = {
    required: "AUTHORITY REQUIRED", verifying: "VERIFYING AUTHORITY",
    verified: "AUTHORITY VERIFIED", rejected: "AUTHORITY REJECTED",
    suspended: "AUTHORITY SUSPENDED",
  };

  function gatewayState(state) {
    byId("authority-gateway").dataset.state = state;
    byId("gateway-state").textContent = gatewayStates[state];
  }

  function closeGateway({ state = "required", message, code = "", focus = true } = {}) {
    unlocked = false;
    readToken = "";
    authorityDeadline = 0;
    accessRevision += 1;
    clearTimeout(expiryTimer);
    clearTimeout(transitionTimer);
    expiryTimer = null;
    transitionTimer = null;
    if (authorityController) authorityController.abort();
    authorityController = null;
    byId("read-token").value = "";
    byId("publish-token").value = "";
    byId("read-form").removeAttribute("aria-busy");
    byId("verify-authority").disabled = false;
    byId("cancel-authority").hidden = true;
    byId("refresh-events").disabled = true;
    byId("format-selection").disabled = true;
    byId("publish-form").querySelector("button[type=submit]").disabled = true;
    byId("certification-workbench").hidden = true;
    byId("certification-workbench").classList.remove("workbench-opening");
    const gateway = byId("authority-gateway");
    gateway.hidden = false;
    gateway.inert = false;
    gateway.removeAttribute("aria-hidden");
    gateway.classList.remove("gateway-departing");
    gatewayState(state);
    byId("skip-link").href = "#authority-gateway";
    byId("skip-link").textContent = "Accéder au sas d'autorité";
    byId("session-state").textContent = state === "suspended" ? "Autorité suspendue" : "Autorité requise";
    const explanation = message || "Accès local fermé. Votre manifeste et vos pièces choisies restent en mémoire dans cet onglet. Présentez un nouveau mandat pour reprendre.";
    display("gateway-progress", code ? "La demande d'accès a été refusée par le backend." : explanation);
    display("gateway-error", code ? `${code} — ${explanation}` : "", code ? "error" : "");
    if (focus) {
      gateway.focus();
      gateway.scrollIntoView({ block: "start", behavior: "instant" });
    }
  }

  function expireAuthority() {
    if (!unlocked) return;
    const remaining = authorityDeadline - performance.now();
    if (remaining > 0) {
      expiryTimer = setTimeout(expireAuthority, remaining);
      return;
    }
    closeGateway({ state: "suspended", message: "Le mandat de lecture a atteint son échéance vérifiée par le serveur. Présentez un nouveau mandat ; votre manifeste et votre sélection sont conservés en mémoire." });
  }

  function hasReadAuthority() {
    if (!unlocked) return false;
    if (performance.now() >= authorityDeadline) {
      expireAuthority();
      return false;
    }
    return true;
  }

  function suspendFromBackend(error) {
    if (error.status !== 401 && error.status !== 403) return false;
    closeGateway({ state: "suspended", code: error.code,
      message: `${error.message} Présentez un nouveau mandat de lecture ; votre travail est conservé en mémoire.` });
    return true;
  }

  function openWorkbench(verification, remaining) {
    unlocked = true;
    authorityDeadline = performance.now() + remaining;
    expiryTimer = setTimeout(expireAuthority, remaining);
    gatewayState("verified");
    byId("cancel-authority").hidden = true;
    display("gateway-error", "");
    display("gateway-progress", "Mandat vérifié par VANTA. Accès au dossier d'audit accordé.", "success");
    const gateway = byId("authority-gateway");
    const workbench = byId("certification-workbench");
    gateway.inert = true;
    gateway.setAttribute("aria-hidden", "true");
    workbench.hidden = false;
    workbench.classList.add("workbench-opening");
    const hideGateway = () => {
      gateway.hidden = true;
      gateway.classList.remove("gateway-departing");
      workbench.classList.remove("workbench-opening");
    };
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      hideGateway();
    } else {
      gateway.classList.add("gateway-departing");
      // Visual cleanup only: the workshop and its controls are available now.
      transitionTimer = setTimeout(hideGateway, 400);
    }
    byId("skip-link").href = "#main";
    byId("skip-link").textContent = "Accéder à l'atelier";
    byId("authority-validity").textContent = `Lecture autorisée jusqu'au ${new Date(verification.expires_at * 1000).toISOString()} (heure du serveur).`;
    byId("session-state").textContent = "Lecture autorisée";
    byId("refresh-events").disabled = false;
    byId("publish-form").querySelector("button[type=submit]").disabled = false;
    selectionState();
    showWorkspace(activeWorkspace);
    const heading = byId("main");
    heading.focus();
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  async function loadContracts() {
    const results = await Promise.allSettled([
      api("/api/public/contract"), api("/api/public/policy"), api("/api/public/attestation-key"),
    ]);
    const [contractResult, policyResult, keyResult] = results;
    if (contractResult.status === "fulfilled") {
      const contract = contractResult.value;
      ["jwt-claims", "gateway-jwt-claims"].forEach((id) => {
        const list = byId(id);
        list.replaceChildren();
        Object.entries({ ...contract.jwt.header, ...contract.jwt.claims }).forEach(([key, value]) => addPair(list, key, value));
      });
      showJSON("full-contract", contract);
      showJSON("gateway-full-contract", contract);
      showJSON("manifest-contract", contract.manifest);
      showJSON("disclosure-contract", contract.routes.find((route) => route.path === "/api/disclosures"));
      byId("canonical-python").textContent = contract.manifest.canonicalization.python;
      showJSON("demo-vector", contract.manifest.neutral_vector.value);
      byId("demo-hash").textContent = contract.manifest.neutral_vector.sha256;
      byId("verify-python").textContent = contract.attestation.verification_python;
    }
    if (policyResult.status === "fulfilled") {
      ["policy-description", "gateway-policy-description", "dossier-policy-description"].forEach((id) => {
        byId(id).textContent = policyResult.value.description;
      });
      ["policy-criteria", "gateway-policy-criteria"].forEach((id) => {
        const list = byId(id);
        list.replaceChildren();
        policyResult.value.criteria.forEach((criterion) => {
          const item = document.createElement("li");
          item.textContent = criterion;
          list.append(item);
        });
      });
      byId("additional-policy").textContent = policyResult.value.additional_evidence;
      byId("gateway-additional-policy").textContent = policyResult.value.additional_evidence;
    }
    if (keyResult.status === "fulfilled") {
      showJSON("public-key", keyResult.value);
      showJSON("gateway-public-key", keyResult.value);
    }
    const errors = results.filter((result) => result.status === "rejected");
    if (errors.length) {
      display("public-status", errors.map((result) => describeError(result.reason)).join(" · "), "error");
      display("gateway-public-status", errors.map((result) => describeError(result.reason)).join(" · "), "error");
    } else {
      display("public-status", "Contrats et clé publique disponibles. L'autorité de demande et l'autorité de certification sont distinctes.", "success");
      display("gateway-public-status", "Contrats, politique et clé publique disponibles sans mandat.", "success");
      byId("nav-contract").textContent = "Contrats disponibles";
    }
  }

  function selectionState() {
    byId("selection-count").textContent = `${selected.size} pièce${selected.size > 1 ? "s" : ""} choisie${selected.size > 1 ? "s" : ""}`;
    byId("format-selection").disabled = !unlocked || !selected.size;
  }

  function renderEvents() {
    const list = byId("event-list");
    list.replaceChildren();
    [...events].sort((a, b) => a.timestamp - b.timestamp || a.id.localeCompare(b.id)).forEach((event) => {
      const card = document.createElement("article");
      card.className = "event-card";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.id = `select-${event.id}`;
      checkbox.setAttribute("aria-label", `Inclure ${event.id} dans la sélection documentaire`);
      checkbox.checked = selected.has(event.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) selected.add(event.id); else selected.delete(event.id);
        selectionState();
      });
      const content = document.createElement("div");
      const label = document.createElement("label");
      label.htmlFor = checkbox.id;
      label.textContent = event.id;
      const kind = document.createElement("small");
      kind.textContent = `${event.kind} / ${event.subject}`;
      const metadata = document.createElement("dl");
      metadata.className = "event-metadata";
      const payload = event.payload;
      const system = payload.authority || payload.registry || payload.observer || payload.channel || payload.program || payload.pool || "—";
      addPair(metadata, "Origine", event.case_id);
      addPair(metadata, "Identité", payload.identity_id || event.subject);
      addPair(metadata, "Émetteur", system);
      addPair(metadata, "Intégrité", "SHA-256 fourni par le registre");
      const timestamp = document.createElement("small");
      timestamp.textContent = `${new Date(event.timestamp * 1000).toISOString().replace("T", " ").replace(".000Z", " UTC")} · epoch ${event.timestamp}`;
      const detail = document.createElement("button");
      detail.type = "button";
      detail.textContent = "Consulter la pièce ↗";
      detail.setAttribute("aria-label", `Consulter ${event.id}`);
      detail.addEventListener("click", () => loadDetail(event.id));
      content.append(label, kind, timestamp, metadata, detail);
      card.append(checkbox, content);
      list.append(card);
    });
    byId("event-count").textContent = `${events.length} événements · horodatages historiques UTC`;
    selectionState();
  }

  async function loadDetail(eventId) {
    if (!hasReadAuthority()) return;
    const revision = accessRevision;
    display("detail-status", "Lecture authentifiée en cours…");
    try {
      const event = await api(`${eventsPath}/${encodeURIComponent(eventId)}`, { token: readToken, signal: authorityController.signal });
      if (revision !== accessRevision) return;
      if (!hasReadAuthority()) return;
      showJSON("event-detail", event);
      byId("event-reader-heading").focus();
      display("detail-status", `Pièce ${event.id} · contenu original et empreinte`, "success");
    } catch (error) {
      if (revision !== accessRevision) return;
      if (suspendFromBackend(error)) return;
      byId("event-detail").textContent = "Aucun détail reçu pour cette requête.";
      display("detail-status", describeError(error), "error");
    }
  }

  async function loadEvents() {
    if (!hasReadAuthority()) return;
    const revision = accessRevision;
    byId("refresh-events").disabled = true;
    display("read-status", "Signature et permission soumises au registre…");
    try {
      const data = await api(eventsPath, { token: readToken, signal: authorityController.signal });
      if (revision !== accessRevision) return;
      if (!hasReadAuthority()) return;
      events = data.events;
      const available = new Set(events.map((event) => event.id));
      [...selected].forEach((id) => { if (!available.has(id)) selected.delete(id); });
      renderEvents();
      display("read-status", "Autorisation de lecture acceptée par le backend. Le catalogue est disponible.", "success");
      byId("session-state").textContent = "Lecture autorisée";
      byId("nav-register").textContent = `${events.length} pièces accessibles`;
    } catch (error) {
      if (revision !== accessRevision) return;
      if (suspendFromBackend(error)) return;
      display("read-status", describeError(error), "error");
    } finally {
      if (revision === accessRevision) byId("refresh-events").disabled = !unlocked;
    }
  }

  byId("read-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const token = tokenValue(byId("read-token"));
    byId("read-token").value = "";
    if (token.length > 4096) {
      gatewayState("rejected");
      display("gateway-error", "INVALID_TOKEN — Le mandat dépasse la limite de 4096 octets. Aucun caractère n'a été tronqué ; présentez un jeton conforme.", "error");
      return;
    }
    if (authorityController) authorityController.abort();
    clearTimeout(expiryTimer);
    readToken = "";
    accessRevision += 1;
    const revision = accessRevision;
    authorityController = new AbortController();
    gatewayState("verifying");
    byId("verify-authority").disabled = true;
    byId("cancel-authority").hidden = false;
    byId("read-form").setAttribute("aria-busy", "true");
    display("gateway-error", "");
    display("gateway-progress", "Vérification du mandat et des habilitations par l'autorité…");
    const started = performance.now();
    try {
      const verification = await api("/api/authority/verify", { token, signal: authorityController.signal });
      if (revision !== accessRevision) return;
      if (verification.status !== "AUTHORITY_VERIFIED" || verification.case_id !== caseId
          || !Number.isInteger(verification.valid_for_ms) || !Number.isInteger(verification.expires_at)) {
        throw { code: "HTTP_ERROR", message: "Réponse de l'autorité illisible. L'atelier reste fermé." };
      }
      // Use only the verified server response, never decode JWT claims in JS.
      // Subtract the complete round trip to avoid extending the server lifetime.
      const remaining = verification.valid_for_ms - (performance.now() - started);
      if (remaining <= 0) {
        closeGateway({ state: "suspended", message: "Le mandat est arrivé à échéance pendant sa présentation. Présentez un nouveau mandat pour reprendre." });
        return;
      }
      readToken = token;
      openWorkbench(verification, remaining);
      display("read-status", "Autorité de lecture vérifiée. Chargement du registre…", "success");
      await loadEvents();
    } catch (error) {
      if (revision !== accessRevision) return;
      closeGateway({ state: "rejected", code: error.code || "NETWORK_ERROR", message: error.message });
    } finally {
      if (revision === accessRevision) {
        byId("verify-authority").disabled = false;
        byId("read-form").removeAttribute("aria-busy");
      }
    }
  });

  byId("forget-token").addEventListener("click", () => closeGateway());
  byId("cancel-authority").addEventListener("click", () => {
    closeGateway({ message: "Présentation annulée dans cet onglet. Vous pouvez présenter un autre mandat." });
    byId("read-token").focus();
  });
  byId("renew-authority").addEventListener("click", () => {
    closeGateway({ message: "Présentez un nouveau mandat de lecture. Votre manifeste et votre sélection sont conservés en mémoire." });
    byId("read-token").focus();
  });
  byId("refresh-events").addEventListener("click", loadEvents);
  // Clear bearer values before a browser history cache can retain the document.
  window.addEventListener("pagehide", () => closeGateway({ focus: false }));
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && unlocked) hasReadAuthority();
  });
  document.querySelectorAll('.gateway-document-links a[href^="#"]').forEach((link) => {
    link.addEventListener("click", () => {
      const detail = byId(link.getAttribute("href").slice(1));
      detail.open = true;
      detail.querySelector("summary").focus();
    });
  });

  byId("format-selection").addEventListener("click", () => {
    if (!hasReadAuthority()) return;
    const evidence = events.filter((event) => selected.has(event.id))
      .map((event) => ({ id: event.id, sha256: event.sha256 }))
      .sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    byId("manifest").value = JSON.stringify({
      schema: "VANTA-PROOF/1", case_id: caseId, assertion: "SILENCE_COVERUP", evidence,
    }, null, 2);
    display("manifest-status", "Sélection importée et références triées selon VANTA-PROOF/1. Le brouillon courant remplace la version précédente.");
    byId("nav-proof").textContent = "Sélection importée";
  });
  byId("manifest").addEventListener("input", () => {
    byId("nav-proof").textContent = "Manifeste modifié";
    display("manifest-status", "Le manifeste a changé. Son empreinte signée doit correspondre à cette version.");
  });

  byId("publish-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!hasReadAuthority()) return;
    const revision = accessRevision;
    const button = event.currentTarget.querySelector("button[type=submit]");
    const token = tokenValue(byId("publish-token"));
    byId("publish-token").value = "";
    if (token.length > 4096) {
      display("publish-status", "INVALID_TOKEN — Le mandat dépasse la limite de 4096 octets. Aucun caractère n'a été tronqué.", "error");
      return;
    }
    // Send the editor text unchanged inside the envelope: JSON.parse would
    // silently erase duplicate object keys before the backend can reject them.
    const body = `{"manifest":${byId("manifest").value}}`;
    envelope = null;
    byId("receipt-panel").hidden = true;
    byId("receipt-empty").hidden = false;
    byId("nav-receipt").textContent = "Aucun reçu";
    button.disabled = true;
    display("publish-status", "Autorisation, engagement et politique soumis à l'autorité…");
    try {
      const result = await api("/api/disclosures", { token, method: "POST", body, signal: authorityController.signal });
      if (revision !== accessRevision) return;
      envelope = result;
      const receipt = envelope.receipt;
      // Presentation of the actual signed response; no local certification or
      // signature verification is inferred from the narrative.
      byId("receipt-decision").textContent = receipt.decision;
      const certification = byId("certification-summary");
      certification.replaceChildren();
      addPair(certification, "DOSSIER", receipt.case_id);
      addPair(certification, "ASSERTION", receipt.assertion);
      addPair(certification, "AUTORITÉ ED25519", envelope.signing_key_id);
      byId("receipt-technical").open = false;
      const summary = byId("receipt-summary");
      summary.replaceChildren();
      addPair(summary, "REÇU", receipt.receipt_id);
      addPair(summary, "DOSSIER", receipt.case_id);
      addPair(summary, "ASSERTION", receipt.assertion);
      addPair(summary, "ÉMIS À", `${new Date(receipt.issued_at * 1000).toISOString()} / epoch ${receipt.issued_at}`);
      addPair(summary, "PROOF SHA-256", receipt.proof_sha256);
      addPair(summary, "AUTORITÉ", envelope.signing_key_id);
      byId("receipt-flag").textContent = receipt.flag;
      showJSON("receipt-json", envelope);
      byId("receipt-panel").hidden = false;
      byId("receipt-empty").hidden = true;
      display("publish-status", "CERTIFIED_DISCLOSURE — preuve acceptée, reçu signé Ed25519 par VANTA.", "success");
      byId("nav-receipt").textContent = "Divulgation certifiée";
      showWorkspace("receipts");
      history.replaceState(null, "", "#receipts");
      byId("receipt-heading").focus();
    } catch (error) {
      if (revision !== accessRevision) return;
      // A rejected publication token does not invalidate the distinct read token.
      display("publish-status", describeError(error), "error");
      byId("nav-receipt").textContent = "Aucun reçu";
    } finally { if (revision === accessRevision) button.disabled = !unlocked; }
  });

  byId("show-receipt-verification").addEventListener("click", (event) => {
    event.preventDefault();
    byId("receipt-verification").open = true;
    byId("receipt-verification").querySelector("summary").focus();
  });

  byId("download-receipt").addEventListener("click", () => {
    if (!envelope) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(envelope, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "vanta-disclosure.json";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  loadContracts();
})();
