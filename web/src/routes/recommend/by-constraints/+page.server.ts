// The /recommend pages were retired in #332; /choose answers the same
// question with cited picks. Old links land there.
import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';

export const prerender = true;

export function load(): never {
  redirect(308, `${base}/choose`);
}
