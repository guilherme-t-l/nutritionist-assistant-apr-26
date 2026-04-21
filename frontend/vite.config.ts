import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config: read by `npm run dev` and `npm run build`.
// `defineConfig` is just a typed wrapper that gives editor autocompletion
// for the options object. It's not doing any runtime magic.
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    // When the React app calls fetch("/plan"), the browser sees it as a
    // same-origin request (to :5173). Vite intercepts it and forwards it
    // to the Python backend on :8000. This way we don't need CORS during
    // development — the browser never sees a cross-origin request.
    proxy: {
      "/plan": "http://localhost:8000",
      "/chat": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
