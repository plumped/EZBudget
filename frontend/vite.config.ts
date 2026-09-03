import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Django-Backend läuft separat auf :8000 — der Dev-Server reicht
      // /api-Requests serverseitig durch, damit der Browser alles als
      // gleiche Origin sieht (keine CORS-/Cookie-Klimmzüge nötig).
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: false,
      },
    },
  },
})
