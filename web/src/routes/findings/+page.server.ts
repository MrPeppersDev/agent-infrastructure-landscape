import { liveFindings } from '$lib/findings-live';

export const prerender = true;

export const load = () => ({ findings: liveFindings() });
