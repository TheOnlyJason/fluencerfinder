import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Where the dev server proxies API calls. Defaults to a local backend on :8000
// (run `uvicorn app.main:app --port 8000`). To develop the UI WITHOUT running a
// backend, set VITE_DEV_API to a deployed backend (e.g. the Cloud Run URL) in
// frontend/.env.local — then `npm run dev` works on its own.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_DEV_API || "http://127.0.0.1:8000";
  const apiPaths = ["/search", "/accounts", "/creators", "/imports", "/exports", "/identity", "/health"];

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: Object.fromEntries(
        apiPaths.map((path) => [path, { target, changeOrigin: true, secure: true }])
      ),
    },
  };
});
