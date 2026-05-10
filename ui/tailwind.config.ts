import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      colors: {
        // Main Backgrounds
        'bg-main': '#0a0a0c',
        'bg-card': 'rgba(255, 255, 255, 0.05)',
        'bg-input': 'rgba(0, 0, 0, 0.2)',
        'bg-terminal': '#0f1115',
        'bg-terminal-header': '#1a1d24',

        // Accent Colors
        'accent-cyan': '#22d3ee',
        'accent-cyan-dark': '#0891b2',
        'accent-blue': '#3b82f6',
        'accent-blue-dark': '#2563eb',

        // Status Colors
        'success': '#10b981',
        'success-bg': 'rgba(16, 185, 129, 0.1)',
        'warning': '#f59e0b',
        'error': '#ef4444',
        'error-bg': 'rgba(239, 68, 68, 0.1)',
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
