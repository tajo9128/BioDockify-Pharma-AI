import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

const STATUS_API = "/plugins/_browser_agent/status";
const MODEL_PRESET_API = "/plugins/_browser_agent/model_preset";

const model = {
  loading: true,
  savingPreset: false,
  error: "",
  status: null,

  async openModelSettings() {
    await import("/components/plugins/plugin-settings-store.js");
    await $store.pluginSettingsPrototype.openConfig("_model_config");
  },

  async refreshStatus() {
    this.status = await callJsonApi(STATUS_API, {});
  },

  async savePreset(presetName) {
    this.savingPreset = true;
    try {
      await callJsonApi(MODEL_PRESET_API, {
        action: presetName ? "set" : "clear",
        preset_name: presetName || "",
      });
      this.error = "";
      await this.refreshStatus();
    } catch (error) {
      this.error = error instanceof Error ? error.message : String(error);
      await this.refreshStatus();
    } finally {
      this.savingPreset = false;
    }
  },

  async onOpen() {
    this.loading = true;
    this.error = "";

    try {
      await this.refreshStatus();
    } catch (error) {
      this.status = null;
      this.error = error instanceof Error ? error.message : String(error);
    } finally {
      this.loading = false;
    }
  },

  cleanup() {},
};

export const store = createStore("browserAgentPage", model);
