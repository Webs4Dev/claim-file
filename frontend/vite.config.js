import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: false,
    // Same-origin API calls, so the session cookie works in development.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        // Append the real client IP to X-Forwarded-For, so uvicorn (which
        // reads the rightmost untrusted entry) cannot be fooled by a header
        // the browser sent.
        xfwd: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
