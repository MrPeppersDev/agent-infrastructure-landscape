import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  // landscape.json is 6.4 MB. Bumping the asset inline limit to 0 ensures it's
  // never inlined into JS, and silencing the chunk-size warning keeps `npm run
  // build` clean (the data, not code, is what's large).
  build: {
    assetsInlineLimit: 0,
    chunkSizeWarningLimit: 8000
  }
});
