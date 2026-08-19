import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],

  // Match the tracked directory name exactly for case-sensitive Linux deploys.
  root: path.resolve(import.meta.dirname, 'src/Frontend'),

  envDir: path.resolve(import.meta.dirname),

  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
