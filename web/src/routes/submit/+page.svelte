<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';

  // /submit — system-intake form (issue #28).
  //
  // Two-step UX: (1) edit form, (2) review the exact markdown that will
  // land in the GitHub Issue. The submit button on step 2 navigates to
  // the pre-filled new-issue URL — there is no backend.
  //
  // Validation is local (no libraries) via lib/submit-issue.ts. The
  // section / type / tier / license option lists also live there so
  // this page stays presentation-only.

  import { onMount } from 'svelte';
  import {
    EMPTY_FORM,
    SECTION_OPTIONS,
    TYPE_OPTIONS,
    TIER_OPTIONS,
    LICENSE_OPTIONS,
    COST_PRICING_MODEL_OPTIONS,
    USE_CASE_TAG_VOCAB,
    validateSubmission,
    buildIssueUrl,
    type SubmissionFormState,
    type UseCaseTag
  } from '$lib/submit-issue';

  let form: SubmissionFormState = $state({ ...EMPTY_FORM });
  let step: 'edit' | 'review' = $state('edit');
  let showErrors = $state(false);
  let licenseMode: 'preset' | 'custom' = $state('preset');
  let licenseCustom = $state('');

  // Derived validation; runs every keystroke so disabled-state on the
  // "Review" button stays in sync. Errors render only after the user
  // tries to advance — fewer red borders on first paint.
  const validation = $derived(validateSubmission(form));
  const built = $derived(buildIssueUrl(form));
  const descCount = $derived(form.description.trim().length);

  function effectiveLicense(): string {
    if (licenseMode === 'custom') return licenseCustom.trim();
    return form.license;
  }

  function goReview() {
    // Snapshot the custom license into form.license so the markdown
    // matches the preview.
    if (licenseMode === 'custom') {
      form = { ...form, license: licenseCustom.trim() };
    }
    showErrors = true;
    if (!validation.ok) {
      // Scroll to first error.
      const firstError = Object.keys(validation.errors)[0];
      if (firstError) {
        const el = document.getElementById(`field-${firstError}`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        (el as HTMLInputElement | null)?.focus();
      }
      return;
    }
    step = 'review';
    // Defer to next tick so the review section renders before we scroll.
    requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  function goEdit() {
    step = 'edit';
    requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  function openIssue(e: MouseEvent) {
    // The anchor itself does the navigation; this handler exists only
    // so we can clear the form's "dirty" state if we ever add a
    // beforeunload prompt. For now it's a no-op pass-through.
    if (!validation.ok) {
      e.preventDefault();
      step = 'edit';
      showErrors = true;
    }
  }

  // Restore in-progress submissions across reloads. Stored under a
  // single key; cleared once the user opens the issue URL.
  const STORAGE_KEY = 'mlc:submit:draft';
  onMount(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        form = { ...EMPTY_FORM, ...parsed };
      }
    } catch {
      // ignore — corrupt storage, fresh form is fine
    }
  });

  $effect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(form));
    } catch {
      // ignore — private mode / quota
    }
  });

  function clearDraft() {
    form = { ...EMPTY_FORM };
    licenseMode = 'preset';
    licenseCustom = '';
    showErrors = false;
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }

  function errFor(k: keyof SubmissionFormState): string {
    if (!showErrors) return '';
    return validation.errors[k] ?? '';
  }

  // Phase 2: toggle a use-case tag in form.useCaseTags. Chip UI calls
  // this on click. Tag list stays in vocab order regardless of click
  // order so the issue body is deterministic for the bot's parser.
  function toggleUseCaseTag(tag: UseCaseTag): void {
    const current = form.useCaseTags;
    const next = current.includes(tag)
      ? current.filter((t) => t !== tag)
      : USE_CASE_TAG_VOCAB.filter((v) => current.includes(v) || v === tag);
    form = { ...form, useCaseTags: next as UseCaseTag[] };
  }
</script>

<svelte:head>
  <SeoHead
    title="Submit a System to the AI Agent Memory Landscape"
    description="Submit a new AI memory / agent infrastructure system to the catalog via a pre-filled GitHub Issue."
    path="/submit"
    ogType="website"
  />
</svelte:head>

<article class="submit">
  <header>
    <h1>Submit a system</h1>
    <p class="lede">
      Spotted a system the catalog is missing? Fill this form and we'll
      open a pre-filled GitHub Issue with your submission. A curator
      will verify and slot it into the next ingestion round.
    </p>
    <p class="note">
      No login required for the form itself — but the final step opens a
      GitHub Issue, so you'll need a GitHub account to actually post it.
      Nothing is stored server-side; the form lives in your browser
      until you click "Open issue".
    </p>
  </header>

  {#if step === 'edit'}
    <form
      class="form"
      onsubmit={(e) => {
        e.preventDefault();
        goReview();
      }}
      novalidate
    >
      <section class="group">
        <h2>Identity</h2>

        <div class="field" id="field-name">
          <label for="in-name">
            Name <span class="req">*</span>
          </label>
          <input
            id="in-name"
            type="text"
            bind:value={form.name}
            placeholder="e.g. Mem0, Letta, MemoryBench-v2"
            aria-invalid={!!errFor('name')}
            aria-describedby={errFor('name') ? 'err-name' : undefined}
          />
          {#if errFor('name')}<small id="err-name" class="err">{errFor('name')}</small>{/if}
        </div>

        <div class="field" id="field-url">
          <label for="in-url">
            URL <span class="req">*</span>
          </label>
          <input
            id="in-url"
            type="url"
            bind:value={form.url}
            placeholder="https://example.com"
            aria-invalid={!!errFor('url')}
            aria-describedby={errFor('url') ? 'err-url' : undefined}
          />
          <small class="hint">Canonical project / vendor URL.</small>
          {#if errFor('url')}<small id="err-url" class="err">{errFor('url')}</small>{/if}
        </div>

        <div class="field" id="field-type">
          <label for="in-type">
            Type <span class="req">*</span>
          </label>
          <select
            id="in-type"
            bind:value={form.type}
            aria-invalid={!!errFor('type')}
            aria-describedby={errFor('type') ? 'err-type' : undefined}
          >
            <option value="">— pick one —</option>
            {#each TYPE_OPTIONS as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
          {#if errFor('type')}<small id="err-type" class="err">{errFor('type')}</small>{/if}
        </div>
      </section>

      <section class="group">
        <h2>Placement</h2>

        <div class="field" id="field-section">
          <label for="in-section">
            Section <span class="req">*</span>
          </label>
          <select
            id="in-section"
            bind:value={form.section}
            aria-invalid={!!errFor('section')}
            aria-describedby={errFor('section') ? 'err-section' : undefined}
          >
            <option value="">— pick a section —</option>
            {#each SECTION_OPTIONS as s}
              <option value={s}>{s}</option>
            {/each}
          </select>
          <small class="hint">
            If none fit, choose "other / new section" and explain in the
            subsection / notes.
          </small>
          {#if errFor('section')}<small id="err-section" class="err">{errFor('section')}</small>{/if}
        </div>

        <div class="field" id="field-subsection">
          <label for="in-subsection">Subsection</label>
          <input
            id="in-subsection"
            type="text"
            bind:value={form.subsection}
            placeholder="e.g. graph-memory subset"
          />
          <small class="hint">Optional. Free text.</small>
        </div>

        <div class="field" id="field-tierGuess">
          <label for="in-tier">Tier guess</label>
          <select id="in-tier" bind:value={form.tierGuess}>
            {#each TIER_OPTIONS as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
          <small class="hint">
            Optional. The curator will re-tier if needed — tier is a
            classification, not a quality score.
          </small>
        </div>
      </section>

      <section class="group">
        <h2>Description</h2>

        <div class="field" id="field-description">
          <label for="in-desc">
            Brief description <span class="req">*</span>
            <span class="counter" class:over={descCount > 240}>
              {descCount}/240
            </span>
          </label>
          <textarea
            id="in-desc"
            rows="3"
            bind:value={form.description}
            placeholder="One sentence: what is it, who is it for?"
            aria-invalid={!!errFor('description')}
            aria-describedby={errFor('description') ? 'err-desc' : undefined}
          ></textarea>
          <small class="hint">~140 chars target; 240 hard cap.</small>
          {#if errFor('description')}<small id="err-desc" class="err">{errFor('description')}</small>{/if}
        </div>

        <div class="field" id="field-claims">
          <label for="in-claims">Claims / pitch</label>
          <textarea
            id="in-claims"
            rows="5"
            bind:value={form.claims}
            placeholder="What does the system claim about itself? Benchmarks, throughput, novel ideas — paste their own pitch."
          ></textarea>
          <small class="hint">Optional. Longer free text is fine.</small>
        </div>
      </section>

      <section class="group">
        <h2>Signals</h2>

        <div class="field" id="field-funding">
          <label for="in-funding">Known funding</label>
          <input
            id="in-funding"
            type="text"
            bind:value={form.funding}
            placeholder="$X Series Y (date, lead investor)"
          />
        </div>

        <div class="field" id="field-customers">
          <label for="in-customers">Known customers</label>
          <input
            id="in-customers"
            type="text"
            bind:value={form.customers}
            placeholder="Notable named users / case studies"
          />
        </div>

        <div class="field" id="field-license">
          <label for="in-license">License</label>
          <div class="license-row">
            {#if licenseMode === 'preset'}
              <select
                id="in-license"
                bind:value={form.license}
                style="flex:1"
              >
                {#each LICENSE_OPTIONS as lic}
                  <option value={lic}>{lic || '— skip —'}</option>
                {/each}
              </select>
              <button
                type="button"
                class="link-btn"
                onclick={() => {
                  licenseMode = 'custom';
                  licenseCustom = form.license;
                }}
              >
                free text
              </button>
            {:else}
              <input
                id="in-license"
                type="text"
                bind:value={licenseCustom}
                placeholder="Custom license string"
                style="flex:1"
                oninput={() => {
                  form = { ...form, license: licenseCustom };
                }}
              />
              <button
                type="button"
                class="link-btn"
                onclick={() => {
                  licenseMode = 'preset';
                }}
              >
                dropdown
              </button>
            {/if}
          </div>
        </div>

        <div class="field" id="field-githubUrl">
          <label for="in-gh">GitHub URL</label>
          <input
            id="in-gh"
            type="url"
            bind:value={form.githubUrl}
            placeholder="https://github.com/org/repo"
            aria-invalid={!!errFor('githubUrl')}
            aria-describedby={errFor('githubUrl') ? 'err-gh' : undefined}
          />
          {#if errFor('githubUrl')}<small id="err-gh" class="err">{errFor('githubUrl')}</small>{/if}
        </div>

        <div class="field" id="field-arxivUrl">
          <label for="in-arxiv">Arxiv URL</label>
          <input
            id="in-arxiv"
            type="url"
            bind:value={form.arxivUrl}
            placeholder="https://arxiv.org/abs/…"
            aria-invalid={!!errFor('arxivUrl')}
            aria-describedby={errFor('arxivUrl') ? 'err-arxiv' : undefined}
          />
          {#if errFor('arxivUrl')}<small id="err-arxiv" class="err">{errFor('arxivUrl')}</small>{/if}
        </div>
      </section>

      <section class="group">
        <h2>Cost (Phase 2)</h2>
        <p class="hint" style="margin: -6px 0 12px 0;">
          Optional. The research bot scrapes the vendor pricing page
          when the pricing model is "hosted-api" or "hosted-service"
          and these are blank. If you already know the numbers,
          fill them in — submitter values are never overwritten.
        </p>

        <div class="field" id="field-costInputUsdPerMtok">
          <label for="in-cost-in">Input cost (USD per million tokens)</label>
          <input
            id="in-cost-in"
            type="text"
            inputmode="decimal"
            bind:value={form.costInputUsdPerMtok}
            placeholder="e.g. 3.00"
            aria-invalid={!!errFor('costInputUsdPerMtok')}
            aria-describedby={errFor('costInputUsdPerMtok') ? 'err-cost-in' : undefined}
          />
          {#if errFor('costInputUsdPerMtok')}<small id="err-cost-in" class="err">{errFor('costInputUsdPerMtok')}</small>{/if}
        </div>

        <div class="field" id="field-costOutputUsdPerMtok">
          <label for="in-cost-out">Output cost (USD per million tokens)</label>
          <input
            id="in-cost-out"
            type="text"
            inputmode="decimal"
            bind:value={form.costOutputUsdPerMtok}
            placeholder="e.g. 15.00"
            aria-invalid={!!errFor('costOutputUsdPerMtok')}
            aria-describedby={errFor('costOutputUsdPerMtok') ? 'err-cost-out' : undefined}
          />
          {#if errFor('costOutputUsdPerMtok')}<small id="err-cost-out" class="err">{errFor('costOutputUsdPerMtok')}</small>{/if}
        </div>

        <div class="field" id="field-costPricingModel">
          <label for="in-cost-model">Pricing model</label>
          <select id="in-cost-model" bind:value={form.costPricingModel}>
            {#each COST_PRICING_MODEL_OPTIONS as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
          <small class="hint">
            Tells the bot whether to scrape a vendor pricing page.
            OSS / academic systems usually have no per-token price.
          </small>
        </div>
      </section>

      <section class="group">
        <h2>Capability (Phase 2)</h2>
        <p class="hint" style="margin: -6px 0 12px 0;">
          Optional. Paste benchmark sources — URLs to MMLU / HumanEval /
          memory-eval leaderboards, ideally with the relevant score.
          The bot HEAD-checks each URL and pulls one score; absent
          submission means the bot guesses a capability band marked
          unverified.
        </p>

        <div class="field" id="field-capabilityBenchmarkSources">
          <label for="in-cap-src">Benchmark sources</label>
          <textarea
            id="in-cap-src"
            rows="4"
            bind:value={form.capabilityBenchmarkSources}
            placeholder={'e.g.\nhttps://artificialanalysis.ai/models/foo — MMLU 0.81\nhttps://example.com/leaderboard — HumanEval 0.73'}
          ></textarea>
          <small class="hint">
            One source per line is easiest for the bot to parse. URLs
            with scores beat URLs alone.
          </small>
        </div>
      </section>

      <section class="group">
        <h2>Use-case (Phase 2)</h2>
        <p class="hint" style="margin: -6px 0 12px 0;">
          Pick the use-cases this system is built for. The bot may add
          additional tags from the same controlled vocabulary, but
          will never remove your selections.
        </p>

        <div class="field" id="field-useCaseTags">
          <span class="pseudo-label">Use-case tags</span>
          <div class="chip-row" role="group" aria-label="Use-case tags">
            {#each USE_CASE_TAG_VOCAB as tag}
              <button
                type="button"
                class="chip"
                class:chip-on={form.useCaseTags.includes(tag)}
                aria-pressed={form.useCaseTags.includes(tag)}
                onclick={() => toggleUseCaseTag(tag)}
              >
                {tag}
              </button>
            {/each}
          </div>
          {#if errFor('useCaseTags')}<small class="err">{errFor('useCaseTags')}</small>{/if}
        </div>

        <div class="field" id="field-useCaseTagsOther">
          <label for="in-use-other">Other tags (free-text)</label>
          <input
            id="in-use-other"
            type="text"
            bind:value={form.useCaseTagsOther}
            placeholder="comma-separated; curator may add to vocabulary"
          />
          <small class="hint">
            Use only if the eight tags above genuinely don't cover the
            system's intended use-case.
          </small>
        </div>
      </section>

      <section class="group">
        <h2>Submitter notes</h2>
        <div class="field" id="field-notes">
          <label for="in-notes">Anything else the catalog should know</label>
          <textarea
            id="in-notes"
            rows="4"
            bind:value={form.notes}
            placeholder="Caveats, related systems, disputed claims, conflict-of-interest disclosure, …"
          ></textarea>
        </div>
      </section>

      <div class="actions">
        <button type="button" class="btn-secondary" onclick={clearDraft}>
          Clear draft
        </button>
        <button type="submit" class="btn-primary">
          Review &amp; submit →
        </button>
      </div>

      {#if showErrors && !validation.ok}
        <p class="form-error" role="alert">
          Please fix the highlighted fields before continuing.
        </p>
      {/if}
    </form>
  {:else}
    <section class="review">
      <div class="review-header">
        <h2>Review &amp; submit</h2>
        <p>
          This is the exact issue body that will land on GitHub. The
          title will be <code>{built.title}</code> and the label
          <code>intake</code> will be applied.
        </p>
      </div>

      <pre class="markdown-preview" aria-label="Issue body preview">{built.markdown}</pre>

      <div class="actions">
        <button type="button" class="btn-secondary" onclick={goEdit}>
          ← Back to edit
        </button>
        <a
          class="btn-primary"
          href={built.url}
          target="_blank"
          rel="noopener noreferrer"
          onclick={openIssue}
        >
          Open GitHub Issue ↗
        </a>
      </div>

      <p class="note">
        Clicking opens a new tab on github.com with the fields
        pre-filled. You still have to click GitHub's "Submit new issue"
        button — that's the moment it becomes public.
      </p>
    </section>
  {/if}
</article>

<style>
  .submit {
    max-width: 720px;
    margin: 0 auto;
    padding: 24px 16px 64px;
    color: #d4d4d4;
    font-size: 15px;
    line-height: 1.55;
  }

  .submit header {
    margin-bottom: 28px;
    padding-bottom: 16px;
    border-bottom: 1px solid #2a2a2a;
  }

  .submit h1 {
    font-size: 1.8rem;
    font-weight: 600;
    color: #e8e8e8;
    margin: 0 0 8px 0;
    letter-spacing: -0.015em;
  }

  .lede {
    color: #b8b8b8;
    margin: 0 0 8px 0;
    font-size: 0.98rem;
  }

  .note {
    color: #888;
    font-size: 0.85rem;
    font-style: italic;
    margin: 0;
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .group {
    background: #161616;
    border: 1px solid #262626;
    border-radius: 8px;
    padding: 18px 20px 20px;
  }

  .group h2 {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e8e8e8;
    margin: 0 0 14px 0;
    letter-spacing: -0.005em;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 14px;
  }

  .field:last-child {
    margin-bottom: 0;
  }

  .field label {
    color: #ccc;
    font-size: 0.9rem;
    font-weight: 500;
    display: flex;
    align-items: baseline;
    gap: 6px;
  }

  .req {
    color: #d4845f;
    font-weight: 700;
  }

  .counter {
    margin-left: auto;
    color: #777;
    font-size: 0.78rem;
    font-family: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
  }
  .counter.over {
    color: #d47a7a;
  }

  .field input[type='text'],
  .field input[type='url'],
  .field select,
  .field textarea {
    background: #0e0e0e;
    border: 1px solid #2a2a2a;
    border-radius: 5px;
    padding: 7px 9px;
    color: #e8e8e8;
    font: inherit;
    font-size: 0.92rem;
    font-family: inherit;
  }

  .field textarea {
    font-family: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 0.88rem;
    line-height: 1.5;
    resize: vertical;
    min-height: 60px;
  }

  .field input:focus,
  .field select:focus,
  .field textarea:focus {
    outline: none;
    border-color: #4a8fb5;
    box-shadow: 0 0 0 2px rgba(74, 143, 181, 0.15);
  }

  .field input[aria-invalid='true'],
  .field select[aria-invalid='true'],
  .field textarea[aria-invalid='true'] {
    border-color: #8a4040;
  }

  .field .hint {
    color: #777;
    font-size: 0.78rem;
  }

  .field .err {
    color: #d47a7a;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .license-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .link-btn {
    background: none;
    border: none;
    color: #d4845f;
    cursor: pointer;
    font-size: 0.82rem;
    padding: 2px 4px;
    text-decoration: underline;
  }
  .link-btn:hover {
    color: #e8a37d;
  }

  .actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    align-items: center;
    padding-top: 8px;
  }

  .btn-primary,
  .btn-secondary {
    font: inherit;
    font-size: 0.92rem;
    padding: 9px 16px;
    border-radius: 6px;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    line-height: 1.2;
    border: 1px solid;
  }

  .btn-primary {
    background: #d4845f;
    color: #1a1a1a;
    border-color: #d4845f;
    font-weight: 600;
  }
  .btn-primary:hover {
    background: #e8a37d;
    border-color: #e8a37d;
  }

  .btn-secondary {
    background: transparent;
    color: #b8b8b8;
    border-color: #2a2a2a;
  }
  .btn-secondary:hover {
    background: #1c1c1c;
    color: #e8e8e8;
    border-color: #3a3a3a;
  }

  .form-error {
    margin-top: -8px;
    color: #d47a7a;
    font-size: 0.88rem;
    text-align: right;
  }

  .review {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .review-header h2 {
    font-size: 1.2rem;
    font-weight: 600;
    color: #e8e8e8;
    margin: 0 0 6px 0;
  }
  .review-header p {
    color: #b8b8b8;
    margin: 0;
    font-size: 0.92rem;
  }
  .review-header code {
    font-family: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 0.85em;
    padding: 1px 5px;
    background: #1c1c1c;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    color: #c9a98f;
  }

  .pseudo-label {
    color: #ccc;
    font-size: 0.9rem;
    font-weight: 500;
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
  }

  .chip {
    background: #0e0e0e;
    border: 1px solid #2a2a2a;
    color: #b8b8b8;
    border-radius: 14px;
    padding: 4px 11px;
    font: inherit;
    font-size: 0.82rem;
    cursor: pointer;
    font-family: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
  }
  .chip:hover {
    border-color: #3a3a3a;
    color: #e8e8e8;
  }
  .chip-on {
    background: #2a1f18;
    border-color: #d4845f;
    color: #e8a37d;
  }
  .chip-on:hover {
    background: #38291f;
    color: #f2b894;
  }

  .markdown-preview {
    background: #0e0e0e;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 16px 18px;
    color: #d4d4d4;
    font-family: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 0.82rem;
    line-height: 1.55;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 60vh;
    overflow: auto;
  }
</style>
