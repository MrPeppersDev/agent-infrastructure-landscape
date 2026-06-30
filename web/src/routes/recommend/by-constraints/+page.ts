// Loader for /recommend/by-constraints (issue #98 / Gate 4).
//
// All parsing + ranking happens client-side via $lib/analyses/recommender.
// The shared parent loader supplies the catalog snapshot.

export const prerender = true;
