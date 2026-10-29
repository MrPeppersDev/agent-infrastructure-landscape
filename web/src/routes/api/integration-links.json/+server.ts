// /api/integration-links.json — documented integrations per system (both
// directions), for the stack checker's upgrade advisor in the GitHub Action
// (action/check.mjs): a flagged dependency's replacements that work with the
// rest of the manifest rank first. Prerendered.
import { json } from '@sveltejs/kit';
import { getEdges } from '$lib/data';
import { linksFromEdges } from '../../../../../mcp/src/stack-check';

export const prerender = true;

export const GET = () => json(linksFromEdges(getEdges()));
