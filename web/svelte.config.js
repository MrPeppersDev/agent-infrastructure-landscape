import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      // Build into a staging dir; a postbuild script syncs into ../docs/
      // *without* wiping ../docs/*.md (the project documentation lives
      // alongside the Pages build output — see DECISIONS.md
      // "docs/ holds both project markdown and Pages build output").
      pages: 'build',
      assets: 'build',
      // No SPA fallback — every route is prerendered (see +layout.ts), so
      // the static export is fully resolved HTML, not a SPA shell.
      fallback: undefined,
      precompress: false,
      strict: true
    }),
    paths: {
      // GitHub Pages will serve under /<repo-name>/. Override at build time
      // with BASE_PATH if/when the deploy target changes.
      base: process.env.BASE_PATH ?? ''
    }
  }
};

export default config;
