# Vellum and Hume EVI shutdowns, checked 2026-11-16

Scheduled check-in after the two announced shutdown dates. Both checked on the vendors' own sites; applied with `scripts/apply_reverify.py --date 2026-11-16 results.json` (3 cells, `apply-report.md`).

## Vellum: hosted platform shut down, dates corrected

The record said the hosted Personal Assistant Platform would shut down on 2026-11-02. Vellum's shutdown page (https://www.vellum.ai/vellum-assistant-platform-shutdown) now gives different dates:
- hosted assistants are switched off after a final export starting **2026-11-07**;
- downloads close and hosted data is permanently deleted on **2026-12-13**;
- Vellum no longer actively maintains the open-source repo; a founding engineer maintains a fork, Cadet, for self-hosters.

The page is written in the future tense and undated, so it doesn't confirm the switch-off happened; the record states the vendor's schedule.

## Hume EVI: APIs shut down 2026-11-13

The docs announced the EVI and TTS API shutdown for 2026-11-13 (recorded 2026-10-28). On 2026-11-16, on Hume's own domains:
- the EVI and TTS doc pages (dev.hume.ai/docs/speech-to-speech-evi/overview, /docs/text-to-speech-tts/overview) redirect to the Audio Decisions API docs;
- the hume.ai homepage lists Audio Decision, Expression, Human Feedback and User Testing APIs and Speech Data, with no EVI or Octave TTS;
- `api.hume.ai/v0/evi/configs` returns 404, not an auth error;
- the Audio Decisions changelog starts with that API's launch on 2026-11-02 and doesn't mention EVI.

There is no shutdown statement left to quote: the original notice was on the page that now redirects.
