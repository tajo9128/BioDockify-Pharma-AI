# Chapter 17: Plugin System & Architecture

## 17.1 Plugin Architecture

BioDockify uses a convention-based plugin system:

```
usr/plugins/
├── my-plugin/
│   ├── plugin.yaml          # Plugin manifest
│   ├── api/                 # API endpoints (auto-discovered)
│   ├── tools/               # Agent tools (auto-discovered)
│   ├── webui/               # Frontend components
│   └── extensions/          # Backend extensions
```

---

## 17.2 Plugin Manifest

```yaml
name: my-plugin
description: Custom plugin description
version: 1.0.0
settings_sections:
  - name: My Settings
    key: my_plugin
per_project_config: true
always_enabled: false
```

---

## 17.3 Plugin Discovery

| Folder | Purpose | Discovery |
|--------|---------|-----------|
| `api/` | REST endpoints | Auto-discovered as `/api/<filename>` |
| `tools/` | Agent tools | Auto-discovered for chat commands |
| `webui/` | Frontend components | Auto-discovered as `<x-component>` |
| `extensions/` | Backend hooks | Auto-discovered for lifecycle events |

---

## 17.4 Frontend Component System

Components use Alpine.js with the store factory:

```javascript
import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("myStore", {
  data: [],
  loading: false,
  
  async loadData() {
    this.loading = true;
    this.data = await callJsonApi("my_endpoint", { action: "list" });
    this.loading = false;
  }
});
```

---

## 17.5 Modal System

Open components as modals:
```javascript
window.openModal("components/my-component/my-component.html");
```

Close current modal:
```javascript
window.closeModal();
```

---

## 17.6 Creating Custom Plugins

1. Create folder in `usr/plugins/`
2. Add `plugin.yaml` manifest
3. Add API endpoints in `api/` folder
4. Add frontend in `webui/` folder
5. Restart container

---

## 17.7 Extension Framework

Lifecycle hooks in `hooks.py`:
```python
def on_agent_init(context):
    """Called when agent initializes."""
    pass

def on_message(context, message):
    """Called when user sends message."""
    pass
```

---

## 17.8 Settings Integration

Plugins can expose settings via `plugin.yaml`:
```yaml
settings_sections:
  - name: My Plugin Settings
    key: my_plugin
    fields:
      - name: api_key
        type: password
        label: API Key
```

Settings accessible via:
```python
from helpers.plugins import get_plugin_config
config = get_plugin_config("my_plugin")
api_key = config.get("api_key")
```
