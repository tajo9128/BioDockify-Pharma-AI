import {
  createActionButton,
  copyToClipboard,
} from "/components/messages/action-buttons/simple-action-buttons.js";
import {
  buildDocumentFileActionButtons,
  documentFromLog,
  parseDocumentResult,
} from "../lib/document-actions.js";
import { store as stepDetailStore } from "/components/modals/process-step-detail/step-detail-store.js";
import { store as speechStore } from "/components/chat/speech/speech-store.js";
import {
  buildDetailPayload,
  cleanStepTitle,
  drawProcessStep,
} from "/js/messages.js";

export default async function registerDocumentArtifactHandler(extData) {
  if (extData?.tool_name === "document_artifact") {
    extData.handler = drawDocumentArtifactTool;
  }
}

function drawDocumentArtifactTool({
  id,
  type,
  heading,
  content,
  kvps,
  timestamp,
  agentno = 0,
  ...additional
}) {
  const args = arguments[0];
  const title = cleanStepTitle(heading);
  const displayKvps = { ...kvps };
  const contentText = String(content ?? "");
  const documentResult = parseDocumentResult(contentText);
  const document = documentFromLog(args, documentResult);
  const headerLabels = [
    kvps?._tool_name && { label: kvps._tool_name, class: "tool-name-badge" },
    document?.format && { label: String(document.format).toUpperCase(), class: "tool-name-badge" },
  ].filter(Boolean);

  const actionButtons = buildDocumentFileActionButtons(document);

  if (contentText.trim()) {
    actionButtons.push(
      createActionButton("detail", "", () =>
        stepDetailStore.showStepDetail(buildDetailPayload(args, { headerLabels })),
      ),
      createActionButton("speak", "", () => speechStore.speak(contentText)),
      createActionButton("copy", "", () => copyToClipboard(contentText)),
    );
  }

  const result = drawProcessStep({
    id,
    title,
    code: "DOC",
    classes: undefined,
    kvps: displayKvps,
    content,
    actionButtons: actionButtons.filter(Boolean),
    log: args,
  });
  return result;
}
