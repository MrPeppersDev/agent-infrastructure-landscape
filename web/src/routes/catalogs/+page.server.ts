// /catalogs: the focused views (taxonomy/silos.json) over the one dataset,
// with counts, next to the Atlas that shows everything.

import { getRecords, getRecordCount } from '$lib/data';
import { getSilos, recordsInSilo } from '$lib/silos';
import { lifecycleOf } from '$lib/lifecycle';
import { LIFECYCLE_TONE } from '$lib/lifecycle-labels';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const silos = getSilos().map((s) => {
    const rows = recordsInSilo(records, s);
    const attention = rows.filter((r) => ['warn', 'bad'].includes(LIFECYCLE_TONE[lifecycleOf(r.id).status])).length;
    return {
      id: s.id,
      name: s.name,
      short: s.short,
      tagline: s.tagline,
      audience: s.audience,
      count: rows.length,
      sections: s.sections.length,
      attention,
      family: s.family ?? null
    };
  });
  return { silos, total: getRecordCount() };
};
