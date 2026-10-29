// Catalog counts for every page's copy (titles, meta descriptions, about,
// 404). Computed at prerender time; a few bytes per page.
import { catalogStats } from '$lib/stats';

export const load = () => ({ stats: catalogStats() });
