import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxies /api/* to the Flask server (api.py, port 5057) so the browser
// never needs CORS handling -- same-origin as far as fetch() is concerned.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:5057',
    },
  },
})
