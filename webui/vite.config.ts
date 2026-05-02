import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const localBridgeUrl = process.env.WEBUI_LOCAL_BRIDGE_URL || "http://127.0.0.1:7781";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: localBridgeUrl,
        changeOrigin: false
      }
    }
  },
  preview: {
    port: 4173
  }
});
