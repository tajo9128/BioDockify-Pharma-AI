import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: {
    ignoreBuildErrors: false,
  },
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    unoptimized: true,
  },
  trailingSlash: false,
  // Proxy ALL /api/* requests to backend - KEEP the /api prefix!
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      // All /api/* and /settings/* to backend (KEEP full path)
      { source: "/api/settings", destination: `${backendUrl}/settings` },
      { source: "/api/enhanced/system/status", destination: `${backendUrl}/wizard/system-check` },
      { source: "/api/enhanced/projects", destination: `${backendUrl}/phd/status` },
      { source: "/api/health", destination: `${backendUrl}/health` },
      { source: "/api/models", destination: `${backendUrl}/models` },
      { source: "/api/tags", destination: `${backendUrl}/api/tags` },
      { source: "/v1/models", destination: `${backendUrl}/v1/models` },
      { source: "/v1/chat/completions", destination: `${backendUrl}/v1/chat/completions` },
      // Chat endpoint with full API prefix
      { source: "/api/chat", destination: `${backendUrl}/chat` },
    ];
  },
};

export default nextConfig;

