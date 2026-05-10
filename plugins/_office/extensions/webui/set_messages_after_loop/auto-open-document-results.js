const SYNC_WINDOW_MS = 10 * 60 * 1000;
const DESKTOP_OFFICE_FORMATS = new Set(["odt", "ods", "odp", "docx", "xlsx", "pptx"]);
const syncedDocumentResults = new Set();

export default async function syncDocumentResultsIntoOpenCanvas(context) {
  if (!context?.results?.length || context.historyEmpty) return;

  for (const { args } of context.results) {
    const payload = getDocumentPayload(args);
    if (getToolName(payload) !== "document_artifact") continue;
    if (!shouldSyncOpenOfficeCanvas(args, payload)) continue;

    const document = payload.document && typeof payload.document === "object" ? payload.document : {};
    const path = payload.path || document.path || "";
    const fileId = payload.file_id || document.file_id || "";
    if (!path && !fileId) continue;

    const key = [
      args?.id || "",
      payload.action || "",
      fileId || "",
      path || "",
      payload.version || document.version || "",
    ].join(":");
    if (syncedDocumentResults.has(key)) continue;
    syncedDocumentResults.add(key);

    if (!isOfficeCanvasOrModalOpen() && shouldColdOpenOfficeCanvas(payload, document)) {
      await openOfficeCanvasFromResult({ path, file_id: fileId });
      continue;
    }

    globalThis.setTimeout(async () => {
      if (!isOfficeCanvasOrModalOpen()) return;
      const office = globalThis.Alpine?.store?.("office");
      if (!office || isDirtySameDocument(office, { path, file_id: fileId })) return;
      await office.openSession?.({
        path,
        file_id: fileId,
        refresh: true,
        source: "tool-result-sync",
      });
    }, 0);
  }
}

function getDocumentPayload(args = {}) {
  const contentPayload = parseMaybeJson(args.content);
  const kvpsPayload = args.kvps && typeof args.kvps === "object"
    ? args.kvps
    : parseMaybeJson(args.kvps);
  return {
    ...pickPayloadFields(args),
    ...(contentPayload || {}),
    ...(kvpsPayload || {}),
  };
}

function pickPayloadFields(args = {}) {
  const payload = {};
  for (const key of [
    "_tool_name",
    "tool_name",
    "action",
    "canvas_surface",
    "file_id",
    "format",
    "path",
    "version",
    "last_modified",
  ]) {
    if (args[key] != null && args[key] !== "") payload[key] = args[key];
  }
  return payload;
}

function getToolName(payload = {}) {
  return String(payload._tool_name || payload.tool_name || "").trim();
}

function shouldSyncOpenOfficeCanvas(args = {}, payload = {}) {
  if (!isFresh(args.timestamp, payload.last_modified || payload.document?.last_modified)) return false;
  const action = String(payload.action || "").trim().toLowerCase().replace("-", "_");
  return ["create", "open", "edit", "restore_version"].includes(action);
}

function shouldColdOpenOfficeCanvas(payload = {}, document = {}) {
  const action = String(payload.action || "").trim().toLowerCase().replace("-", "_");
  if (!["create", "open"].includes(action)) return false;
  return DESKTOP_OFFICE_FORMATS.has(documentFormat(payload, document));
}

async function openOfficeCanvasFromResult(document = {}) {
  const canvas = globalThis.Alpine?.store?.("rightCanvas")
    || (await import("/components/canvas/right-canvas-store.js")).store;
  await canvas?.open?.("office", {
    path: document.path || "",
    file_id: document.file_id || "",
    refresh: true,
    source: "tool-result-sync",
  });
}

function documentFormat(payload = {}, document = {}) {
  return String(
    payload.format
      || payload.extension
      || document.extension
      || extensionOf(payload.path || document.path || ""),
  ).trim().toLowerCase().replace(/^\./, "");
}

function extensionOf(path = "") {
  const name = String(path || "").split("?")[0].split("#")[0].split("/").filter(Boolean).pop() || "";
  const index = name.lastIndexOf(".");
  return index >= 0 ? name.slice(index + 1) : "";
}

function isOfficeCanvasAlreadyOpen() {
  const canvas = globalThis.Alpine?.store?.("rightCanvas");
  return Boolean(canvas?.isOpen && canvas?.activeSurfaceId === "office");
}

function isOfficeCanvasOrModalOpen() {
  return Boolean(isOfficeCanvasAlreadyOpen() || isOfficeModalAlreadyOpen());
}

function isOfficeModalAlreadyOpen() {
  return Boolean(
    globalThis.isModalOpen?.("/plugins/_office/webui/main.html")
      || globalThis.isModalOpen?.("plugins/_office/webui/main.html")
      || globalThis.document?.querySelector?.(".office-modal .office-panel, .modal .office-panel"),
  );
}

function isDirtySameDocument(office, document = {}) {
  if (!office?.dirty || !office?.session) return false;
  const path = String(document.path || "");
  const fileId = String(document.file_id || "");
  return Boolean(
    (fileId && office.session.file_id === fileId)
      || (path && office.session.path === path),
  );
}

function isFresh(...timestamps) {
  const now = Date.now();
  for (const value of timestamps) {
    const time = parseTimestamp(value);
    if (time && now - time < SYNC_WINDOW_MS) return true;
  }
  return false;
}

function parseTimestamp(value) {
  if (!value) return 0;
  if (typeof value === "number") return value > 1e12 ? value : value * 1000;
  const parsed = Date.parse(String(value));
  return Number.isFinite(parsed) ? parsed : 0;
}

function parseMaybeJson(value) {
  if (!value) return null;
  if (typeof value === "object") return value;
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed.startsWith("{")) return null;
  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}
