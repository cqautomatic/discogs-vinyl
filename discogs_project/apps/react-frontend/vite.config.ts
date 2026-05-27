import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['apple-touch-icon.png', 'icon-192.png', 'icon-512.png'],
      manifest: {
        name:             'Vinyl Collection',
        short_name:       'Vinyl',
        description:      'Browse your Discogs collection offline',
        theme_color:      '#1a1a1a',
        background_color: '#1a1a1a',
        display:          'standalone',
        orientation:      'portrait',
        start_url:        '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          {
            src:     'icon-512.png',
            sizes:   '512x512',
            type:    'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        // Cache the built app shell
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        // Cache Discogs thumbnail images for up to 30 days
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/i\.discogs\.com\/.*/i,
            handler:    'CacheFirst',
            options: {
              cacheName: 'discogs-images',
              expiration: {
                maxEntries:    500,
                maxAgeSeconds: 60 * 60 * 24 * 30,
              },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api':    { target: 'http://localhost:3001', changeOrigin: true },
      '/health': { target: 'http://localhost:3001', changeOrigin: true },
    },
  },
});
