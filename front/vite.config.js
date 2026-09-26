import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// O build vai para ../web, que a API (FastAPI) serve em /web/. Na demo não precisa de Node nem internet.
// Em desenvolvimento (npm run dev), /api e /fotos são repassados para a API na porta 8000.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/web/",
  build: { outDir: "../web", emptyOutDir: true },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/fotos": "http://localhost:8000",
    },
  },
});
