import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/search": "http://127.0.0.1:8000",
      "/accounts": "http://127.0.0.1:8000",
      "/creators": "http://127.0.0.1:8000",
      "/imports": "http://127.0.0.1:8000",
      "/exports": "http://127.0.0.1:8000",
      "/identity": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
