import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls when VITE_API_BASE_URL is unset (empty string in .env.local).
    // Direct requests (default http://localhost:3001) bypass this — CORS is already
    // configured on the Node API for http://localhost:5173.
    proxy: {
      '/api': { target: 'http://localhost:3001', changeOrigin: true },
      '/health': { target: 'http://localhost:3001', changeOrigin: true },
    },
  },
});
