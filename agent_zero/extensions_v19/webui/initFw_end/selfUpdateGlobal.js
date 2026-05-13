import { store } from "/components/settings/external/biodockify-update-store.js";

export default async function biodockifyUpdateGlobal(ctx) {
  store.checkForUpdate();
}
