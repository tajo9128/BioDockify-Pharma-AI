import {
  createActionButton,
  copyToClipboard,
} from "/components/messages/action-buttons/simple-action-buttons.js";

function basename(path = "") {
  const value = String(path || "").split("?")[0].split("#")[0];
  return value.split("/").filter(Boolean).pop() || "document";
}

export function parseDocumentResult(content) {
  if (!content || typeof content !== "string") return {};
  try {
    const parsed = JSON.parse(content);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function documentFromLog(args = {}, result = {}) {
  const kvps = args?.kvps || {};
  const document = result.document && typeof result.document === "object"
    ? result.document
    : {};
  return {
    file_id: kvps.file_id || document.file_id || "",
    path: kvps.path || document.path || "",
    title: kvps.title || kvps.basename || document.basename || "",
    format: kvps.format || kvps.extension || document.extension || "",
    version: kvps.version || document.version || "",
    last_modified: kvps.last_modified || document.last_modified || "",
  };
}

export async function openOfficeCanvas(kvps = {}) {
  const canvas = globalThis.Alpine?.store?.("rightCanvas")
    || (await import("/components/canvas/right-canvas-store.js")).store;
  await canvas?.open?.("office", {
    path: kvps.path || "",
    file_id: kvps.file_id || "",
    refresh: true,
    source: "message-action",
  });
}

export function downloadDocument(doc = {}) {
  const path = String(doc.path || "");
  if (!path) return;
  const link = globalThis.document.createElement("a");
  link.href = `/api/download_work_dir_file?path=${encodeURIComponent(path)}`;
  link.download = String(doc.title || basename(path));
  globalThis.document.body.appendChild(link);
  link.click();
  globalThis.document.body.removeChild(link);
}

export function buildDocumentFileActionButtons(document = {}) {
  const hasTarget = Boolean(document?.path || document?.file_id);
  const buttons = [];
  if (hasTarget) {
    buttons.push(createActionButton("dock_to_right", "Open in canvas", () => openOfficeCanvas(document)));
  }
  if (document?.path) {
    buttons.push(
      createActionButton("download", "Download", () => downloadDocument(document)),
      createActionButton("content_copy", "Path", () => copyToClipboard(document.path)),
    );
  }
  return buttons;
}
