<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';

  // /about — embedded "how to read this" explainer (issue #21).
  //
  // Single-column, ~600px max width, semantic HTML. We deliberately don't
  // pull aggregates from the loader: the headline counts (523 / 67 / 247)
  // are stable enough that hardcoding them avoids a data dependency on
  // this page. A regenerated-on-build note keeps the reader honest if
  // the catalog grows.
  //
  // Tier badge and status pill samples reuse the same CSS shape and
  // colours as TableRow.svelte so the visual mapping is obvious — but
  // they're locally scoped here (no shared component) because Phase-3/4
  // owners shouldn't be forced to refactor a presentational sample for
  // an explainer page.
</script>

<svelte:head>
  <SeoHead
    title="About: How to Read the AI Agent Memory Landscape"
    description="How to read the AI Agent Infrastructure Landscape: tiers, taxonomy axes, cell status, and edge types."
    path="/about"
    ogType="website"
  />
</svelte:head>

<article class="about">
  <header>
    <h1>How to read this</h1>
    <p class="lede">
      A landscape catalog of AI memory systems — products, frameworks, papers, and
      theoretical proposals — built as the substrate for cross-system comparison,
      adoption signal, and trend analysis.
    </p>
  </header>

  <section>
    <h2>What this is</h2>
    <p>
      <strong>523 systems</strong> across 22+ sections, scored on
      <strong>67 columns</strong> (memory model, claims, performance, deployment,
      governance, &hellip;), connected by <strong>247 typed edges</strong> (built-on,
      cites, succeeds, &hellip;).
    </p>
    <p class="note">
      Numbers are hardcoded from <code>landscape.json</code> at last commit; the
      true count is whatever the table view shows on first load.
    </p>
  </section>

  <section>
    <h2>Tier badges</h2>
    <p>
      Every record carries an ordinal tier from <strong>T1</strong> (most
      battle-tested) to <strong>T5</strong> (most speculative). Tier is
      <em>not</em> a quality score — a T5 manifesto and a T1 commercial product
      are different artefacts, both worth tracking.
    </p>
    <ul class="tier-list">
      <li>
        <span class="tier-badge t1">T1</span>
        <span>Battle-tested. Real customers, measurable enterprise adoption (commercial + mature OSS).</span>
      </li>
      <li>
        <span class="tier-badge t2">T2</span>
        <span>Established / mature OSS. Significant traction, clear maintainer team, in production at known users.</span>
      </li>
      <li>
        <span class="tier-badge t3">T3</span>
        <span>Peer-reviewed. Published at a recognised venue (ACL, EMNLP, NeurIPS, ICLR, &hellip;) with code.</span>
      </li>
      <li>
        <span class="tier-badge t4">T4</span>
        <span>Preprint / unpublished. arXiv (or similar) with implementation but not yet peer-reviewed.</span>
      </li>
      <li>
        <span class="tier-badge t5">T5</span>
        <span>Theoretical or informal. Idea-stage; blog post, manifesto, taxonomy entry, no code.</span>
      </li>
    </ul>
  </section>

  <section>
    <h2>The 7 taxonomy axes</h2>
    <p>
      Each record is placed on seven independent axes. A record can have multiple
      values per axis (e.g. Mem0 is vector + graph + kv on the storage axis);
      exactly one value per axis is marked primary.
    </p>
    <dl class="axes">
      <dt>Storage</dt>
      <dd>Where memory data sits — <code>vector</code> / <code>graph</code> / <code>kv</code> / <code>file</code> / <code>latent</code> / <code>hybrid</code> / &hellip;</dd>

      <dt>Retrieval</dt>
      <dd>How reads happen — <code>semantic</code> / <code>structural</code> / <code>hybrid</code> / <code>parametric</code> / &hellip;</dd>

      <dt>Persistence</dt>
      <dd>Durability of the memory — <code>session</code> / <code>process</code> / <code>persistent</code> / &hellip;</dd>

      <dt>Update</dt>
      <dd>How memory gets written — <code>explicit</code> / <code>implicit</code> / <code>batch</code> / &hellip;</dd>

      <dt>Unit</dt>
      <dd>Granularity of what's stored — <code>fact</code> / <code>chunk</code> / <code>event</code> / <code>trajectory</code> / &hellip;</dd>

      <dt>Governance</dt>
      <dd>Who decides what gets remembered — <code>auto</code> / <code>curated</code> / <code>mixed</code> / &hellip;</dd>

      <dt>Conflict</dt>
      <dd>How contradictions resolve — <code>latest</code> / <code>vote</code> / <code>merge</code> / <code>ignore</code> / &hellip;</dd>
    </dl>
  </section>

  <section>
    <h2>Cell status indicators</h2>
    <p>
      Every cell in the 67-column table carries a status so a reader can tell
      "data" from "we tried and found nothing" from "doesn't apply here".
    </p>
    <ul class="status-list">
      <li>
        <span class="status-pill real-data">real-data</span>
        <span>Actual data, sourced and (usually) cited.</span>
      </li>
      <li>
        <span class="status-pill not-applicable">not-applicable</span>
        <span>Column doesn't apply to this record (e.g. funding on a research paper).</span>
      </li>
      <li>
        <span class="status-pill depth-floor-reached">depth-floor-reached</span>
        <span>Searched in good faith; no info found. Honest gap.</span>
      </li>
      <li>
        <span class="status-pill no-data">no-data</span>
        <span>Placeholder for an un-researched cell. Rare in terminal data.</span>
      </li>
    </ul>
  </section>

  <section>
    <h2>How edges work</h2>
    <p>
      The Graph and Lineages views are powered by a separate file of typed
      directed edges. Multiple edges between the same pair are allowed if the
      type differs (Letta <em>succeeds</em> MemGPT <em>and</em> is by the
      <em>same team as</em> MemGPT — both useful).
    </p>
    <ul class="edge-list">
      <li><code>built-on</code> — source's product is implemented on top of target (target is a dependency or runtime).</li>
      <li><code>extends</code> — source extends or generalises target's method, keeping the core idea.</li>
      <li><code>forks</code> — source is a literal code fork of target.</li>
      <li><code>integrates-with</code> — source has a first-class integration / connector / adapter to target.</li>
      <li><code>competes-with</code> — positioned by the market (or themselves) as alternatives in the same buyer's mind.</li>
      <li><code>inspired-by</code> — source cites target as conceptual inspiration without building on or extending it.</li>
      <li><code>cites</code> — source's paper cites target's paper; populated from Semantic Scholar.</li>
      <li><code>same-team-as</code> — same authors, lab, or company across two systems.</li>
      <li><code>succeeds</code> — explicit successor / next-version by the same team (e.g. MemGPT &rarr; Letta).</li>
    </ul>
  </section>

  <section>
    <h2>Methodology &amp; provenance</h2>
    <p>Every entry was sourced from one of:</p>
    <ul>
      <li>Curated lists (Agent-Memory-Paper-List, Awesome-GraphMemory).</li>
      <li>Survey papers (<code>arxiv.org/abs/2512.13564</code>, <code>arxiv.org/abs/2508.10824</code>).</li>
      <li>Benchmark leaderboards (LongMemEval, LoCoMo, ConvoMem).</li>
      <li>Vendor websites and academic venue pages.</li>
      <li>Targeted research-agent sweeps (~25 agents over multiple rounds).</li>
    </ul>
    <p>
      Coverage of the memory-shaped core: <strong>~88–92%</strong> as of the
      last terminal pass. URLs were verified at time of entry. Claims (the
      right-hand columns) are vendor-stated unless otherwise marked.
    </p>
    <p>
      <strong>Scope.</strong> The catalog covers memory systems for AI
      <em>and</em> the adjacent infrastructure that touches them — training
      platforms and dataset stores, generic vector / search systems, and
      agent frameworks regardless of whether they ship a first-party memory
      layer. The goal is comprehensive landscape coverage of the sphere, not
      a strict memory-only filter. Coverage of the adjacent categories is
      lower than the memory core and being expanded incrementally.
    </p>
  </section>

  <section>
    <h2>Acknowledgements &amp; complementary resources</h2>
    <ul class="links">
      <li>
        <a href="https://dbdb.io" target="_blank" rel="noopener noreferrer">dbdb.io</a>
        — Carnegie Mellon's database-of-databases. Same form, different domain;
        roughly 17 systems overlap with this catalog.
      </li>
      <li>
        <a href="https://github.com/WangXFng/Agent-Memory-Paper-List" target="_blank" rel="noopener noreferrer">
          Agent-Memory-Paper-List
        </a>
        — source curated list for the research-side entries.
      </li>
      <li>
        <a href="https://github.com/Applied-Machine-Learning-Lab/Awesome-GraphMemory" target="_blank" rel="noopener noreferrer">
          Awesome-GraphMemory
        </a>
        — source curated list for graph-memory systems.
      </li>
      <li>
        <a
          href="https://github.com/MrPeppersDev/agent-infrastructure-landscape"
          target="_blank"
          rel="noopener noreferrer">GitHub repo</a
        >
        — issue tracker, build plan, decision log, raw <code>landscape.json</code>.
      </li>
      <li>
        <a
          href="https://github.com/MrPeppersDev/library-consortium"
          target="_blank"
          rel="noopener noreferrer">Library Consortium</a
        >
        — sister project: a governed knowledge substrate for AI systems (quality
        gates, evidence-weight, provenance). LC answers "how do I run a memory
        substrate"; this catalog answers "what does the broader landscape look
        like".
      </li>
    </ul>
  </section>
</article>

<style>
  .about {
    max-width: 640px;
    margin: 0 auto;
    padding: 24px 16px 64px;
    color: #d4d4d4;
    font-size: 15px;
    line-height: 1.6;
  }

  .about header {
    margin-bottom: 32px;
    padding-bottom: 16px;
    border-bottom: 1px solid #2a2a2a;
  }

  .about h1 {
    font-size: 1.8rem;
    font-weight: 600;
    color: #e8e8e8;
    margin: 0 0 8px 0;
    letter-spacing: -0.015em;
  }

  .lede {
    color: #aaa;
    margin: 0;
    font-size: 0.98rem;
  }

  .about section {
    margin-bottom: 28px;
  }

  .about h2 {
    font-size: 1.15rem;
    font-weight: 600;
    color: #e8e8e8;
    margin: 0 0 10px 0;
    letter-spacing: -0.005em;
  }

  .about p {
    margin: 0 0 10px 0;
  }

  .about p.note {
    color: #777;
    font-size: 0.85rem;
    font-style: italic;
  }

  .about strong {
    color: #e8e8e8;
    font-weight: 600;
  }

  .about code {
    font-family: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 0.85em;
    padding: 1px 5px;
    background: #1c1c1c;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    color: #c9a98f;
  }

  .about ul {
    margin: 0 0 10px 0;
    padding-left: 0;
    list-style: none;
  }

  .about ul.tier-list li,
  .about ul.status-list li {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 8px;
  }

  .about ul.tier-list span:last-child,
  .about ul.status-list span:last-child {
    flex: 1;
  }

  .about ul.edge-list,
  .about ul.links,
  .about section > ul:not(.tier-list):not(.status-list) {
    padding-left: 18px;
    list-style: disc;
  }

  .about ul.edge-list li,
  .about ul.links li,
  .about section > ul:not(.tier-list):not(.status-list) li {
    margin-bottom: 5px;
  }

  .about a {
    color: #d4845f;
    text-decoration: none;
  }

  .about a:hover {
    text-decoration: underline;
  }

  /* Tier badge — same visual as TableRow.svelte. */
  .tier-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.04em;
    line-height: 1.4;
    border: 1px solid;
    min-width: 24px;
    text-align: center;
    flex-shrink: 0;
  }
  .tier-badge.t1 {
    background: #1f3a26;
    color: #8fc99a;
    border-color: #2c5235;
  }
  .tier-badge.t2 {
    background: #1f2e3a;
    color: #8fb3c9;
    border-color: #2c4253;
  }
  .tier-badge.t3 {
    background: #321f3a;
    color: #b58fc9;
    border-color: #492c53;
  }
  .tier-badge.t4 {
    background: #3a2e1f;
    color: #c9a98f;
    border-color: #53432c;
  }
  .tier-badge.t5 {
    background: #2a2a2a;
    color: #999;
    border-color: #3a3a3a;
  }

  /* Status pill — purpose-built sample so the explainer doesn't depend on
     the still-evolving table-cell render. */
  .status-pill {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 3px;
    font-family: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 10.5px;
    font-weight: 600;
    line-height: 1.5;
    border: 1px solid;
    flex-shrink: 0;
    min-width: 130px;
    text-align: center;
  }
  .status-pill.real-data {
    background: #15241a;
    color: #7ab78b;
    border-color: #234231;
  }
  .status-pill.not-applicable {
    background: #1c1c1c;
    color: #777;
    border-color: #2a2a2a;
  }
  .status-pill.depth-floor-reached {
    background: #2a2014;
    color: #b88a5a;
    border-color: #45341f;
  }
  .status-pill.no-data {
    background: #2a1a1a;
    color: #b87a7a;
    border-color: #452a2a;
  }

  /* Axis definition list. */
  .axes {
    margin: 0 0 10px 0;
  }
  .axes dt {
    font-weight: 600;
    color: #e8e8e8;
    margin-top: 8px;
  }
  .axes dt:first-child {
    margin-top: 0;
  }
  .axes dd {
    margin: 0 0 0 0;
    padding-left: 0;
    color: #b8b8b8;
  }
</style>
