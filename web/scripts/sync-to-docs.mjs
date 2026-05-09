// Postbuild: sync web/build/ → ../docs/ without clobbering project markdown.
//
// Why this script exists: docs/ predates the Pages build target — it's where
// BUILD-PLAN.md, DECISIONS.md, and SCHEMA.md live. SvelteKit's adapter-static
// wipes its output directory before writing. So we build into web/build/ and
// then copy *only the new files* into ../docs/, preserving any *.md or
// .nojekyll files already there. Build artefacts from a previous run that
// no longer exist (orphaned hashed JS chunks) are deleted, but only those
// that look like build artefacts (under _app/, plus index.html and
// __data.json at the root).

import { rm, cp, readdir, stat, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const buildDir = path.resolve(__dirname, '..', 'build');
const docsDir = path.resolve(__dirname, '..', '..', 'docs');

if (!existsSync(buildDir)) {
  console.error(`sync-to-docs: build dir not found: ${buildDir}`);
  process.exit(1);
}
if (!existsSync(docsDir)) {
  await mkdir(docsDir, { recursive: true });
}

// 1. Remove old build artefacts from docs/ (keep markdown / hidden files).
const oldAppDir = path.join(docsDir, '_app');
if (existsSync(oldAppDir)) {
  await rm(oldAppDir, { recursive: true, force: true });
}
for (const f of ['index.html', '__data.json']) {
  const p = path.join(docsDir, f);
  if (existsSync(p)) await rm(p, { force: true });
}

// 2. Copy everything from build/ into docs/.
async function copyAll(src, dst) {
  for (const entry of await readdir(src)) {
    const s = path.join(src, entry);
    const d = path.join(dst, entry);
    const st = await stat(s);
    if (st.isDirectory()) {
      await mkdir(d, { recursive: true });
      await copyAll(s, d);
    } else {
      await cp(s, d, { force: true });
    }
  }
}
await copyAll(buildDir, docsDir);

console.log(`sync-to-docs: wrote build artefacts into ${docsDir}`);
