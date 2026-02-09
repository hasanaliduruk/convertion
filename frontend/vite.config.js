import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,      // Needed for Docker to expose the port
    strictPort: true,
    port: 5173,      // Matches your docker-compose
    watch: {
      usePolling: true // Fixes hot-reload issues in Docker
    }
  }
})