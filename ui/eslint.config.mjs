import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // TypeScript 核心规则 (重新启用)
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": ["warn", { "argsIgnorePattern": "^_" }],
      "@typescript-eslint/no-non-null-assertion": "warn",
      "@typescript-eslint/ban-ts-comment": "warn",

      // React 核心规则 (重新启用)
      "react-hooks/exhaustive-deps": "warn",
      "react/no-unescaped-entities": "error",
      "react/display-name": "warn",

      // Next.js 核心规则 (重新启用)
      "@next/next/no-img-element": "warn",
      "@next/next/no-html-link-for-pages": "error",

      // 一般安全性与质量规则 (重新启用)
      "prefer-const": "warn",
      "no-console": ["warn", { "allow": ["warn", "error"] }],
      "no-debugger": "error",
      "no-mixed-spaces-and-tabs": "error",
    },
  },
];

export default eslintConfig;
