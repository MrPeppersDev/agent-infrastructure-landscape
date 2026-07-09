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
      // SPA fallback for the one client-only route (/compare/custom,
      // refs #134 — 528 records → ~139k pairs, not prerenderable). GitHub
      // Pages serves 404.html for any unknown path, so the fallback shell
      // boots the client router there: /compare/custom resolves to its
      // route; genuinely unknown paths render src/routes/+error.svelte
      // (which replaced the old hand-authored static/404.html). Every
      // other route is still prerendered (see +layout.ts).
      fallback: '404.html',
      precompress: false,
      strict: true
    }),
    paths: {
      // GitHub Pages will serve under /<repo-name>/. Override at build time
      // with BASE_PATH if/when the deploy target changes.
      base: process.env.BASE_PATH ?? ''
    },
    prerender: {
      // /feed.xml is emitted by scripts/generate-feed.mjs after the Vite
      // build, so SvelteKit's prerender crawler can't see it. Every page's
      // <link rel="alternate"> points to it, so we tell the crawler to
      // ignore that single missing href instead of failing the build.
      handleHttpError: ({ path, referrer, message }) => {
        if (path.endsWith('/feed.xml')) return;
        throw new Error(`${message} (linked from ${referrer})`);
      }
    }
  }
};

export default config;
