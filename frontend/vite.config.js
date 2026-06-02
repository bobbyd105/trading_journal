import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiProxy = {
  target: 'http://localhost:8000',
  changeOrigin: true,
};

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/trades': apiProxy,
      '/playbooks': apiProxy,
      '/tags': apiProxy,
      '/attachments': apiProxy,
      '/analytics': apiProxy,
      '/psychology': apiProxy,
      '/health': apiProxy,
    },
  },
});
