import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "client", "src"),
    },
  },
  root: path.resolve(__dirname, "client"),
  build: {
    outDir: path.resolve(__dirname, "dist"),
    emptyOutDir: true,
  },
  server: {
    port: 7173,
    host: true,
    proxy: {
      "/api": {
        target: "http://localhost:7000",
        changeOrigin: true,
      },
      // Orchestrator Agent's own /chat -- a real network call reaching the
      // real running agent process (port 7021), same pattern as the claims
      // solution's /adjuster-orchestrator proxy. Path prefix stripped so
      // "/orchestrator-agent/chat" reaches that process's "/chat".
      "/orchestrator-agent": {
        target: process.env.PROXY_ORCHESTRATOR_AGENT_URL || "http://localhost:7021",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/orchestrator-agent/, ""),
      },
      // L0 Self-Service Agent's own /chat -- same real-process pattern as
      // /orchestrator-agent above (port 7014, see agents/l0_self_service/server.py).
      "/l0-agent": {
        target: process.env.PROXY_L0_SELF_SERVICE_AGENT_URL || "http://localhost:7014",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/l0-agent/, ""),
      },
    },
  },
});
