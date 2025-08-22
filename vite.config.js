import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5001  // Избегаем конфликта с ботом на 5000
  },
  preview: {
    host: '0.0.0.0',
    port: 5000,   // Используем тот же порт, что и основной сервер
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  },

});