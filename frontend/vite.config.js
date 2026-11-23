import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The browser only talks to this dev server; /api is proxied to the backend,
// so every request is same-origin and CORS stays closed.
// API_PROXY_TARGET overrides the backend address (default: localhost:8000).
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // No CORS headers from the dev server: the SPA and /api are same-origin.
    cors: false,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: false,
      },
    },
  },
  build: {
    sourcemap: false,
    rolldownOptions: {
      output: {
        // Strip console/debugger calls (including those inside bundled
        // libraries) from the production bundle.
        minify: { compress: { dropConsole: true, dropDebugger: true }, mangle: true },
      },
    },
  },
});
