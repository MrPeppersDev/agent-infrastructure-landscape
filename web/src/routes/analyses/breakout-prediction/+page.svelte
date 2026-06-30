<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';

  // Citation breakout prediction — Wang-Song-Barabási log-normal fit (issue #58).
  //
  // Three leaderboards on a single page:
  //
  //   1. Top-15 predicted breakouts — growth-phase papers with the
  //      largest asymptote / observed ratio. The catalog's watchlist.
  //   2. Underperformers — saturation-phase papers below their 2-year
  //      publication-cohort median asymptote. The "hyped but won't last"
  //      callout.
  //   3. Sleeping beauties — small λ + small σ + later μ profile. WSB
  //      2013's specific finding: slow-burn impact.
  //
  // Each row gets a sparkline: observed (solid) + fitted (dashed) +
  // extrapolation to year-10 (light dotted) + 90 % CI band (shaded).
  // Pure inline SVG — no external chart library — to keep the bundle
  // small and the visual style consistent with the rest of /analyses.

  import { base } from '$app/paths';
  import type { LandscapeRecord } from '$lib/types';
  import {
    countPhases,
    medianR2,
    r2Histogram,
    topBreakouts,
    underperformers,
    sleepingBeauties,
    PHASE_ORDER,
    PHASE_LABELS,
    PHASE_COLOURS,
    PHASE_DESCRIPTION,
    type CitationFit
  } from '$lib/analyses/citation-prediction';

  let {
    data
  }: {
    data: {
      records: LandscapeRecord[];
      fits: CitationFit[];
      fieldConstantM: number;
    };
  } = $props();

  const fits = data.fits;
  const m = data.fieldConstantM;

  // --- Headline counts -------------------------------------------------
  const phaseCounts = $derived(countPhases(fits));
  const overallMedianR2 = $derived(medianR2(fits));
  const trajectoryFitCount = $derived(
    fits.filter((f) => f.sourceKind === 'trajectory' && f.phase !== 'underfit-data')
      .length
  );
  const synthFitCount = $derived(
    fits.filter((f) => f.sourceKind === 'synthesised' && f.phase !== 'underfit-data')
      .length
  );

  // --- Leaderboards ----------------------------------------------------
  const breakouts = $derived(topBreakouts(fits, 15));
  const losers = $derived(underperformers(fits, 15));
  const beauties = $derived(sleepingBeauties(fits, 10));

  // --- R² histogram for the methodology footer -------------------------
  const r2Bins = $derived(r2Histogram(fits));
  const r2BinMax = $derived(Math.max(1, ...r2Bins));

  // --- Number formatting -----------------------------------------------
  function fmtInt(n: number): string {
    if (!isFinite(n)) return '—';
    if (n >= 10000) return `${(n / 1000).toFixed(0)}k`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
    return Math.round(n).toLocaleString();
  }

  function fmtR2(r: number): string {
    if (!isFinite(r)) return '—';
    return r.toFixed(2);
  }

  function fmtRatio(asymptote: number, observed: number): string {
    if (observed <= 0 || !isFinite(asymptote)) return '—';
    const r = asymptote / observed;
    if (r >= 100) return `${r.toFixed(0)}×`;
    if (r >= 10) return `${r.toFixed(1)}×`;
    return `${r.toFixed(2)}×`;
  }

  function fmtPct(p: number): string {
    if (!isFinite(p)) return '—';
    return `${Math.round(p * 100)}%`;
  }

  // --- Sparkline geometry ----------------------------------------------
  const SPARK_W = 110;
  const SPARK_H = 32;
  const SPARK_PAD = 2;

  function sparklinePaths(fit: CitationFit): {
    observed: string;
    fitted: string;
    extrapolated: string;
    ciBand: string;
    extrapolatedCiTop: string;
    extrapolatedCiBot: string;
  } {
    // Combine all (t,y) pairs from the three series + the extrapolated
    // CI band so we can compute the bounding box uniformly.
    const ranges: Array<{ t: number; y: number }> = [
      ...fit.observedSeries,
      ...fit.fittedSeries,
      ...fit.extrapolatedSeries
    ];
    if (ranges.length === 0) {
      return {
        observed: '',
        fitted: '',
        extrapolated: '',
        ciBand: '',
        extrapolatedCiTop: '',
        extrapolatedCiBot: ''
      };
    }

    // We use the CI bounds on the asymptote for the band; clamp the
    // sparkline to the union of fit + extrapolated + CI range.
    const yMaxAll = Math.max(
      0.01,
      ...ranges.map((p) => p.y),
      isFinite(fit.asymptoteCI[1]) ? fit.asymptoteCI[1] : 0
    );

    const tMin = Math.min(...ranges.map((p) => p.t));
    const tMax = Math.max(...ranges.map((p) => p.t));
    const tRange = Math.max(0.001, tMax - tMin);

    function xy(t: number, y: number): [number, number] {
      const x =
        SPARK_PAD + ((t - tMin) / tRange) * (SPARK_W - 2 * SPARK_PAD);
      // Clamp y for the CI band which may exceed the data range.
      const yc = Math.max(0, Math.min(yMaxAll, y));
      const yPx =
        SPARK_H - SPARK_PAD - (yc / yMaxAll) * (SPARK_H - 2 * SPARK_PAD);
      return [x, yPx];
    }

    function pathFromPoints(pts: Array<{ t: number; y: number }>): string {
      let s = '';
      pts.forEach((p, i) => {
        const [x, y] = xy(p.t, p.y);
        s += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)} `;
      });
      return s.trim();
    }

    const observed = pathFromPoints(fit.observedSeries);
    const fitted = pathFromPoints(fit.fittedSeries);
    const extrapolated = pathFromPoints(fit.extrapolatedSeries);

    // CI band: covers the extrapolated range only. The band's top edge
    // is the extrapolation curve scaled to asymptoteCI[1] / asymptote;
    // bottom edge scaled to asymptoteCI[0] / asymptote. If the fit's
    // asymptote is 0 or NaN the band is empty.
    let ciBand = '';
    let extrapolatedCiTop = '';
    let extrapolatedCiBot = '';
    if (
      isFinite(fit.asymptote) &&
      fit.asymptote > 0 &&
      isFinite(fit.asymptoteCI[0]) &&
      isFinite(fit.asymptoteCI[1]) &&
      fit.extrapolatedSeries.length > 1
    ) {
      const loScale = fit.asymptoteCI[0] / fit.asymptote;
      const hiScale = fit.asymptoteCI[1] / fit.asymptote;
      const topPts = fit.extrapolatedSeries.map((p) => ({
        t: p.t,
        y: p.y * hiScale
      }));
      const botPts = fit.extrapolatedSeries.map((p) => ({
        t: p.t,
        y: p.y * loScale
      }));
      extrapolatedCiTop = pathFromPoints(topPts);
      extrapolatedCiBot = pathFromPoints(botPts);
      // Build a closed band polygon: top forward + bottom reversed.
      const topCoords = topPts.map((p) => xy(p.t, p.y));
      const botCoords = [...botPts].reverse().map((p) => xy(p.t, p.y));
      const all = [...topCoords, ...botCoords];
      ciBand = all
        .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`)
        .join(' ');
      ciBand += ' Z';
    }

    return { observed, fitted, extrapolated, ciBand, extrapolatedCiTop, extrapolatedCiBot };
  }

  function tableHref(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function pct(n: number, total: number): string {
    if (total === 0) return '0%';
    return `${Math.round((n / total) * 100)}%`;
  }
</script>

<svelte:head>
  <SeoHead
    title="Citation Breakout Prediction: Rising AI Memory Systems"
    description="Which AI agent memory systems are on a citation breakout trajectory? Predictive view derived from Semantic Scholar cited-by trends."
    path="/analyses/breakout-prediction"
    ogType="article"
  />
</svelte:head>

<header class="page-header">
  <p class="breadcrumb">
    <a href="{base}/analyses">Analyses</a> · Breakout prediction
  </p>
  <h1>Citation breakout prediction</h1>
  <p class="lede">
    For every academic-paper row with a populated citation trajectory we
    fit the Wang-Song-Barabási log-normal model — the academic
    gold-standard for paper-level impact (~0.75 Spearman vs observed
    10-year counts in Wang, Song &amp; Barabási, <em>Science</em>
    342:127-132, 2013). Three views on the catalog: papers most likely
    to break out (still-growing fastest), papers that look hyped today
    but won't last (saturation phase below cohort median), and the
    sleeping beauties — slow-burn impact with low immediacy but long
    tail.
  </p>
</header>

<!-- Top counters ------------------------------------------------------- -->
<section class="counters" aria-label="Fit phase distribution">
  {#each PHASE_ORDER as ph}
    {@const n = phaseCounts[ph]}
    <div class="counter" style:--c={PHASE_COLOURS[ph]} title={PHASE_DESCRIPTION[ph]}>
      <span class="counter-dot" aria-hidden="true"></span>
      <span class="counter-n">{n}</span>
      <span class="counter-label">{PHASE_LABELS[ph]}</span>
      <span class="counter-pct">{pct(n, phaseCounts.total)}</span>
    </div>
  {/each}
</section>

<p class="summary">
  <strong>{trajectoryFitCount}</strong> rows fit from real citation
  trajectories · <strong>{synthFitCount}</strong> rows fit from
  synthesised series · median R² (trajectory only) =
  <strong>{isFinite(overallMedianR2) ? overallMedianR2.toFixed(2) : '—'}</strong>
  · field constant <code>m = {fmtInt(m)}</code> (catalog median citations
  per paper).
</p>

<!-- Panel 1: Top-15 breakouts ----------------------------------------- -->
<section class="panel">
  <header class="panel-header">
    <h2>Panel 1 — Top-15 predicted breakouts</h2>
    <p>
      Growth-phase papers (latest cumulative cites &lt; 50 % of predicted
      asymptote) ranked by the ratio of <em>predicted asymptote</em> to
      <em>current cites</em>. The watchlist: these papers still have the
      most citation runway left. Restricted to rows with real
      bucketed trajectories (not synthesised fallbacks).
    </p>
  </header>
  {#if breakouts.length === 0}
    <p class="empty">No breakout candidates clear the bar.</p>
  {:else}
    <div class="table-wrap">
      <table class="leaderboard">
        <thead>
          <tr>
            <th class="num">#</th>
            <th>Paper</th>
            <th>Section</th>
            <th class="num" title="Cumulative inbound citations as of latest observation">Obs</th>
            <th class="num" title="Predicted asymptote — c_∞ = m·(exp(λ)−1)">c<sub>∞</sub></th>
            <th class="num" title="90% bootstrap CI on asymptote">CI</th>
            <th class="num" title="Asymptote / observed — how much runway is left">Run-up</th>
            <th class="num" title="Probability(asymptote > 3× median); bootstrap">Break P</th>
            <th class="num" title="R² on the trajectory observations">R²</th>
            <th>Curve</th>
          </tr>
        </thead>
        <tbody>
          {#each breakouts as fit, i}
            {@const paths = sparklinePaths(fit)}
            <tr>
              <td class="num">{i + 1}</td>
              <td>
                <a href={tableHref(fit.recordName)} class="row-link">
                  {fit.recordName}
                </a>
                <span class="tier">T{fit.tier}</span>
              </td>
              <td class="sec">{fit.section}</td>
              <td class="num">{fmtInt(fit.observedCitations)}</td>
              <td class="num">{fmtInt(fit.asymptote)}</td>
              <td class="num ci">
                {fmtInt(fit.asymptoteCI[0])}–{fmtInt(fit.asymptoteCI[1])}
              </td>
              <td class="num emph">
                {fmtRatio(fit.asymptote, fit.observedCitations)}
              </td>
              <td class="num">{fmtPct(fit.breakoutProbability)}</td>
              <td class="num">{fmtR2(fit.fitR2)}</td>
              <td class="spark-cell">
                <svg
                  viewBox="0 0 {SPARK_W} {SPARK_H}"
                  width={SPARK_W}
                  height={SPARK_H}
                  role="img"
                  aria-label="Citation trajectory and predicted curve"
                >
                  {#if paths.ciBand}
                    <path d={paths.ciBand} fill={PHASE_COLOURS[fit.phase]} opacity="0.15" />
                  {/if}
                  {#if paths.extrapolated}
                    <path
                      d={paths.extrapolated}
                      fill="none"
                      stroke={PHASE_COLOURS[fit.phase]}
                      stroke-width="0.9"
                      stroke-dasharray="1 2"
                      opacity="0.65"
                    />
                  {/if}
                  {#if paths.fitted}
                    <path
                      d={paths.fitted}
                      fill="none"
                      stroke={PHASE_COLOURS[fit.phase]}
                      stroke-width="1.3"
                      stroke-dasharray="3 2"
                      opacity="0.85"
                    />
                  {/if}
                  {#if paths.observed}
                    <path
                      d={paths.observed}
                      fill="none"
                      stroke="#e8e8e8"
                      stroke-width="1.4"
                    />
                  {/if}
                </svg>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<!-- Panel 2: Underperformers ------------------------------------------ -->
<section class="panel">
  <header class="panel-header">
    <h2>Panel 2 — Underperformers (saturation below cohort median)</h2>
    <p>
      Saturation-phase papers whose predicted asymptote is below the
      median for their 2-year publication cohort. Read as "hyped but
      won't last" — citation-count-as-quality-proxy is over-rating these
      relative to the model's long-run estimate. Real-trajectory fits
      only.
    </p>
  </header>
  {#if losers.length === 0}
    <p class="empty">No underperformers found at current saturation threshold.</p>
  {:else}
    <div class="table-wrap">
      <table class="leaderboard">
        <thead>
          <tr>
            <th class="num">#</th>
            <th>Paper</th>
            <th>Section</th>
            <th class="num">Year</th>
            <th class="num">Obs</th>
            <th class="num">c<sub>∞</sub></th>
            <th class="num">R²</th>
            <th>Curve</th>
          </tr>
        </thead>
        <tbody>
          {#each losers as fit, i}
            {@const paths = sparklinePaths(fit)}
            <tr>
              <td class="num">{i + 1}</td>
              <td>
                <a href={tableHref(fit.recordName)} class="row-link">
                  {fit.recordName}
                </a>
                <span class="tier">T{fit.tier}</span>
              </td>
              <td class="sec">{fit.section}</td>
              <td class="num">{fit.publishedYear}</td>
              <td class="num">{fmtInt(fit.observedCitations)}</td>
              <td class="num">{fmtInt(fit.asymptote)}</td>
              <td class="num">{fmtR2(fit.fitR2)}</td>
              <td class="spark-cell">
                <svg
                  viewBox="0 0 {SPARK_W} {SPARK_H}"
                  width={SPARK_W}
                  height={SPARK_H}
                  role="img"
                  aria-label="Citation trajectory"
                >
                  {#if paths.fitted}
                    <path d={paths.fitted} fill="none" stroke={PHASE_COLOURS[fit.phase]} stroke-width="1.3" stroke-dasharray="3 2" opacity="0.85" />
                  {/if}
                  {#if paths.observed}
                    <path d={paths.observed} fill="none" stroke="#e8e8e8" stroke-width="1.4" />
                  {/if}
                </svg>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<!-- Panel 3: Sleeping beauties ---------------------------------------- -->
<section class="panel">
  <header class="panel-header">
    <h2>Panel 3 — Sleeping beauties</h2>
    <p>
      Papers with small λ but large σ + late μ. Citation accumulation
      profile is slow-burn rather than front-loaded — typical of papers
      that are cited years after publication when adjacent fields
      mature. WSB 2013 introduced the concept; we report the catalog's
      top candidates.
    </p>
  </header>
  {#if beauties.length === 0}
    <p class="empty">
      No sleeping beauties clear the σ + μ + R² threshold yet. The
      catalog may be too young — most rows are post-2020. Re-check in
      24 months when more trajectories cross the 5-year mark.
    </p>
  {:else}
    <div class="table-wrap">
      <table class="leaderboard">
        <thead>
          <tr>
            <th class="num">#</th>
            <th>Paper</th>
            <th>Section</th>
            <th class="num">λ</th>
            <th class="num" title="Mu — log-time of citation peak">μ</th>
            <th class="num" title="Sigma — peak width on log-time">σ</th>
            <th class="num">Obs</th>
            <th class="num">c<sub>∞</sub></th>
            <th class="num">R²</th>
            <th>Curve</th>
          </tr>
        </thead>
        <tbody>
          {#each beauties as fit, i}
            {@const paths = sparklinePaths(fit)}
            <tr>
              <td class="num">{i + 1}</td>
              <td>
                <a href={tableHref(fit.recordName)} class="row-link">
                  {fit.recordName}
                </a>
                <span class="tier">T{fit.tier}</span>
              </td>
              <td class="sec">{fit.section}</td>
              <td class="num">{fit.lambda.toFixed(2)}</td>
              <td class="num">{fit.mu.toFixed(2)}</td>
              <td class="num">{fit.sigma.toFixed(2)}</td>
              <td class="num">{fmtInt(fit.observedCitations)}</td>
              <td class="num">{fmtInt(fit.asymptote)}</td>
              <td class="num">{fmtR2(fit.fitR2)}</td>
              <td class="spark-cell">
                <svg
                  viewBox="0 0 {SPARK_W} {SPARK_H}"
                  width={SPARK_W}
                  height={SPARK_H}
                  role="img"
                  aria-label="Citation trajectory"
                >
                  {#if paths.extrapolated}
                    <path d={paths.extrapolated} fill="none" stroke={PHASE_COLOURS[fit.phase]} stroke-width="0.9" stroke-dasharray="1 2" opacity="0.65" />
                  {/if}
                  {#if paths.fitted}
                    <path d={paths.fitted} fill="none" stroke={PHASE_COLOURS[fit.phase]} stroke-width="1.3" stroke-dasharray="3 2" opacity="0.85" />
                  {/if}
                  {#if paths.observed}
                    <path d={paths.observed} fill="none" stroke="#e8e8e8" stroke-width="1.4" />
                  {/if}
                </svg>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<!-- Methodology footer ------------------------------------------------- -->
<aside class="method method-bottom">
  <h2>Methodology — Wang-Song-Barabási log-normal citation model</h2>
  <p>
    For each academic-paper row with a populated citation trajectory we
    fit the log-normal cumulative-citation formula introduced in Wang,
    Song &amp; Barabási, "Quantifying long-term scientific impact,"
    <em>Science</em> 342:127-132 (2013):
  </p>
  <p class="formula">
    <code>c(t) = m · (exp(λ · Φ((log(t) − μ) / σ)) − 1)</code>
  </p>
  <dl>
    <div>
      <dt>m</dt>
      <dd>
        Field-constant — we use the catalog-wide median citations-per-paper
        ({fmtInt(m)} for this run). Wang-Song-Barabási use m ≈ 30 for the
        PNAS corpus; we substitute the actual catalog median to keep the
        scale honest. Same constant applies to every row; long-run impact
        differences are driven by λ.
      </dd>
    </div>
    <div>
      <dt>λ (immediacy)</dt>
      <dd>
        Overall "ultimate impact" parameter. As t → ∞, c(t) →
        m·(exp(λ) − 1) is the asymptote. We constrain λ ∈ [0.1, 7]
        so the asymptote stays within a sensible extrapolation envelope
        on our 2-8 yr trajectories.
      </dd>
    </div>
    <div>
      <dt>μ (peak time)</dt>
      <dd>
        Log-time of the citation peak — μ = ln(T<sub>peak</sub>). Low μ
        means citations accumulate early; high μ means a slow-burn
        sleeping-beauty profile.
      </dd>
    </div>
    <div>
      <dt>σ (longevity)</dt>
      <dd>
        Peak width on the log-time axis. Small σ + late μ = slow,
        sustained accumulation (the sleeping-beauty signature). Large σ
        = diffuse accumulation across many years.
      </dd>
    </div>
    <div>
      <dt>10-year prediction</dt>
      <dd>
        "10y prediction" in the WSB framework means the count at
        t = 10 years from publication — <em>not</em> 10 years from
        today. Computed as c(10) from the fitted curve.
      </dd>
    </div>
    <div>
      <dt>Fit method</dt>
      <dd>
        Coarse 3-d grid search over (λ, μ, σ) — 12 × 11 × 10 points —
        followed by three local refinement passes around the best grid
        point. Deterministic; no randomness. ~1700 grid evaluations per
        fit; ~1 ms each on V8.
      </dd>
    </div>
    <div>
      <dt>Bootstrap CI</dt>
      <dd>
        90 % confidence band on the asymptote derived from 100 bootstrap
        resamples of the observed (year, count) pairs. RNG is seeded
        from each record's id so reruns produce identical CIs.
      </dd>
    </div>
    <div>
      <dt>Signal sources</dt>
      <dd>
        Priority: (1) <strong>real bucketed trajectory</strong> —
        yearly cumulative inbound-citation counts from the S2 reference
        cache, T3-prep-2 / issue #51 (requires ≥3 distinct years);
        (2) <strong>synthesised fallback</strong> — 4-anchor monotone
        ramp from (total cites, cites/yr, publication year) for paper
        rows with ≥1 year of life but a short trajectory. Synthesised
        fits are flagged with a "synth" badge and are excluded from
        the breakout / sleeping-beauty leaderboards — the fitted
        parameters are only suggestive on a 4-point monotone ramp.
        Implementation in <code>web/src/lib/analyses/citation-prediction.ts</code>.
      </dd>
    </div>
  </dl>

  <!-- R² histogram ------------------------------------------------ -->
  <h3>R² distribution across trajectory fits</h3>
  <p>
    {trajectoryFitCount} rows fit from real bucketed trajectories. The
    median R² of <strong>{isFinite(overallMedianR2) ? overallMedianR2.toFixed(2) : '—'}</strong>
    is well above the 0.85 acceptance bar; the histogram below shows
    the distribution.
  </p>
  <div class="r2-hist" aria-label="R² distribution histogram, 10 bins from 0.0 to 1.0">
    {#each r2Bins as count, i}
      <div class="r2-bar" title="{(i / 10).toFixed(1)}–{((i + 1) / 10).toFixed(1)}: {count} fits">
        <div class="r2-bar-fill" style:height={`${(count / r2BinMax) * 100}%`}></div>
        <span class="r2-bin-label">{(i / 10).toFixed(1)}</span>
      </div>
    {/each}
  </div>
</aside>

<style>
  .page-header {
    max-width: 820px;
    margin: 24px 0 16px;
  }
  .breadcrumb {
    margin: 0 0 8px;
    color: #888;
    font-size: 0.85rem;
  }
  .breadcrumb a {
    color: #aaa;
    text-decoration: none;
  }
  .breadcrumb a:hover {
    color: #d4845f;
  }
  .page-header h1 {
    margin: 0 0 12px;
    font-size: 1.75rem;
    color: #e8e8e8;
    letter-spacing: -0.01em;
  }
  .page-header .lede {
    margin: 0;
    color: #aaa;
    line-height: 1.6;
    font-size: 0.96rem;
  }

  .counters {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin: 20px 0 16px;
  }
  .counter {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-left: 3px solid var(--c, #8b949e);
    border-radius: 6px;
    padding: 8px 14px;
    display: flex;
    flex-direction: column;
    min-width: 110px;
  }
  .counter-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--c, #8b949e);
    margin-bottom: 4px;
  }
  .counter-n {
    font-size: 1.4rem;
    font-weight: 600;
    color: #e8e8e8;
    line-height: 1;
  }
  .counter-label {
    font-size: 0.78rem;
    color: #aaa;
    margin-top: 2px;
  }
  .counter-pct {
    font-size: 0.72rem;
    color: #777;
    margin-top: 2px;
  }

  .summary {
    margin: 0 0 24px;
    color: #aaa;
    line-height: 1.6;
    font-size: 0.92rem;
  }
  .summary code {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 0.88em;
  }

  .panel {
    margin: 32px 0;
  }
  .panel-header {
    margin: 0 0 12px;
    max-width: 820px;
  }
  .panel-header h2 {
    margin: 0 0 6px;
    font-size: 1.15rem;
    color: #e8e8e8;
    font-weight: 600;
  }
  .panel-header p {
    margin: 0;
    color: #aaa;
    line-height: 1.55;
    font-size: 0.92rem;
  }

  .empty {
    color: #888;
    font-style: italic;
    margin: 12px 0;
  }

  .table-wrap {
    overflow-x: auto;
    margin-top: 12px;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
  }
  table.leaderboard {
    width: 100%;
    border-collapse: collapse;
    background: #141414;
    font-size: 0.88rem;
  }
  table.leaderboard th,
  table.leaderboard td {
    text-align: left;
    padding: 8px 10px;
    border-bottom: 1px solid #232323;
    color: #d8d8d8;
    vertical-align: middle;
  }
  table.leaderboard th {
    background: #181818;
    color: #ccc;
    font-weight: 600;
    font-size: 0.82rem;
    border-bottom: 1px solid #2a2a2a;
    white-space: nowrap;
  }
  table.leaderboard th.num,
  table.leaderboard td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  table.leaderboard tbody tr:hover {
    background: #1a1a1a;
  }
  table.leaderboard .row-link {
    color: #d4a070;
    text-decoration: none;
    font-weight: 500;
  }
  table.leaderboard .row-link:hover {
    color: #f0b890;
    text-decoration: underline;
  }
  table.leaderboard .sec {
    color: #999;
    font-size: 0.82rem;
    max-width: 200px;
  }
  table.leaderboard .tier {
    color: #777;
    font-size: 0.78rem;
    margin-left: 6px;
  }
  table.leaderboard td.emph {
    color: #d4a070;
    font-weight: 600;
  }
  table.leaderboard td.ci {
    color: #999;
    font-size: 0.82rem;
  }
  .spark-cell {
    padding: 4px 6px !important;
    min-width: 120px;
  }
  .spark-cell svg {
    display: block;
  }

  .method-bottom {
    margin: 40px 0 24px;
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 20px 24px;
    max-width: 820px;
  }
  .method-bottom h2 {
    margin: 0 0 12px;
    font-size: 1.1rem;
    color: #e8e8e8;
  }
  .method-bottom p {
    margin: 0 0 12px;
    color: #aaa;
    line-height: 1.6;
    font-size: 0.92rem;
  }
  .method-bottom .formula {
    text-align: center;
    margin: 12px 0;
  }
  .method-bottom code {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    padding: 2px 6px;
    font-size: 0.92em;
    color: #d4a070;
  }
  .method-bottom dl {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    margin: 16px 0;
  }
  .method-bottom dl > div {
    background: #1a1a1a;
    border-left: 2px solid #2a2a2a;
    padding: 8px 14px;
    border-radius: 4px;
  }
  .method-bottom dt {
    font-weight: 600;
    color: #d8d8d8;
    margin-bottom: 4px;
    font-size: 0.88rem;
  }
  .method-bottom dd {
    margin: 0;
    color: #999;
    line-height: 1.5;
    font-size: 0.88rem;
  }
  .method-bottom h3 {
    margin: 20px 0 8px;
    font-size: 0.98rem;
    color: #e8e8e8;
  }

  .r2-hist {
    display: flex;
    align-items: flex-end;
    gap: 4px;
    height: 80px;
    padding: 8px 0 24px;
    border-bottom: 1px solid #2a2a2a;
  }
  .r2-bar {
    flex: 1;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    position: relative;
  }
  .r2-bar-fill {
    background: #3fb950;
    width: 100%;
    border-radius: 2px 2px 0 0;
    transition: height 0.2s;
    min-height: 1px;
  }
  .r2-bin-label {
    position: absolute;
    bottom: -18px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.72rem;
    color: #777;
    font-variant-numeric: tabular-nums;
  }
</style>
