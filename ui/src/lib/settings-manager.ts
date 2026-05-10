// Settings manager module - handles application settings

// Centralized config - use relative URLs for Docker compatibility
export const API_BASE = '';  // Empty = same origin (works with Next.js proxy)
export const OLLAMA_BASE = '/api';  // Proxied via Next.js to backend

interface Settings {
  llm: {
    provider: 'openai' | 'ollama';
    apiKey?: string;
    ollamaUrl?: string;
  };
  database: {
    host: string;
    user: string;
    password: string;
  };
  elsevier?: {
    apiKey?: string;
  };
}

// Default settings
const defaultSettings: Settings = {
  llm: {
    provider: 'ollama',
    ollamaUrl: OLLAMA_BASE,
    apiKey: '',
  },
  database: {
    host: 'bolt://localhost:7687',
    user: 'neo4j',
    password: 'password',
  },
  elsevier: {
    apiKey: '',
  },
};

// In-memory storage (in production, persist to database)
let currentSettings: Settings = { ...defaultSettings };

// Get current settings
export function getSettings(): Settings {
  return { ...currentSettings };
}

// Save settings
export function saveSettings(settings: Settings): void {
  currentSettings = { ...settings };
}

// Reset settings to default
export function resetSettings(): void {
  currentSettings = { ...defaultSettings };
}

// Get specific setting
export function getSetting(path: string): any {
  const keys = path.split('.');
  let value: any = currentSettings;

  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key];
    } else {
      return undefined;
    }
  }

  return value;
}
