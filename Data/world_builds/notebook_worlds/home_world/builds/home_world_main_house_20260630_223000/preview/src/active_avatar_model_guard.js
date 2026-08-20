export function isKiraRuntimeAvatar(label = "", candidateId = "") {
  const normalizedLabel = String(label || "").trim().toLowerCase();
  const normalizedCandidate = String(candidateId || "").trim().toLowerCase();
  return normalizedCandidate === "kira"
    || normalizedLabel === "kira"
    || normalizedLabel.includes("kira first");
}

export function shouldRevokeKiraRuntimeModel(shellState = {}, label = "", displayModelUrl = "") {
  if (!isKiraRuntimeAvatar(label, shellState.active_candidate)) return false;
  if (!String(displayModelUrl || "").trim()) return true;
  const selection = shellState.active_body_selection;
  return selection?.enforced === true && selection?.valid !== true;
}

export function isCurrentAvatarModelLoad({
  requestGeneration,
  currentGeneration,
  requestedUrl,
  currentUrl,
  markerPresent,
} = {}) {
  return Number.isInteger(requestGeneration)
    && requestGeneration === currentGeneration
    && String(requestedUrl || "") !== ""
    && requestedUrl === currentUrl
    && markerPresent === true;
}
