---
name: topic-feasibility-screener
description: Screen CSV or Stata DTA datasets and academic literature for feasible empirical research topics with visual HTML reports, broad topic brainstorming, real literature searches, theory/data feasibility scoring, and second-pass validation for top topics. Use when the user gives a dataset and a rough or open-ended paper idea, asks whether a topic is theoretically and empirically viable, wants many possible topic directions from existing data, wants literature-gap validation, wants DID/panel/OLS feasibility checks, or wants a research-topic dashboard before committing to a thesis, finance/accounting/economics/management paper, DID design, mechanism test, robustness test, or variable pairing.
---

# Topic Feasibility Screener

Use this skill to turn a rough empirical idea plus a `.csv` or `.dta` dataset into a visual research-topic dashboard. The skill must brainstorm topic directions beyond the exact variables named by the user, search enough real literature to judge theoretical support, run minimal empirical screens, compute integrated feasibility scores, and perform deeper validation for the top three topics.

## Core Stance

- Treat significance as a screening signal, not as proof of a publishable causal effect.
- Prefer theory-first topics with credible identification, usable variation, sufficient observations, interpretable variable definitions and defensible data sources.
- Require two forms of feasibility before recommending a topic: literature/theory feasibility and data/model feasibility.
- Do not merely pick among variables in the user's phrase. Use the dataset to brainstorm broader outcome-treatment-mechanism-heterogeneity directions.
- Never recommend a topic only because one p-value is small. Always state what identification design is still needed.
- Make the main output visual: an HTML report with score charts, ranked tables, literature evidence and second-pass validation. CSV/JSON files are supporting artifacts only.
- If the dataset contains sensitive or private data, avoid exposing raw rows in the response. Summarize variable names, counts and model outputs.

## Workflow

1. **Clarify the minimal input.**
   - Required: path to one `.csv` or `.dta`.
   - Helpful: rough topic phrase, e.g. "data-resource recognition and reputation", "digital finance and common prosperity", "ESG and financing constraints".
   - Optional: user-specified outcome variables, key explanatory variables, controls, firm identifier and time variable.

2. **Brainstorm topic directions before narrowing.**
   - Identify variable themes such as digital transformation, reputation, financing constraints, earnings management, analyst environment, audit/governance, innovation, ESG/green transition and capital-market response.
   - Generate topic directions from combinations of:
     - outcome/key variable pairs;
     - mechanism candidates;
     - heterogeneity candidates;
     - likely designs: DID/event study, panel fixed effects, mechanism tests, IV/DML possibilities.
   - For each topic direction, write a one-sentence research question, a plausible theory gap and a mechanism sketch.
   - Avoid treating the user's rough phrase as a closed variable list.

3. **Probe the literature and theory.**
   - If `$nature-academic-search` or academic-search MCP tools are available, use them first for multi-source searches.
   - Search enough real literature for each serious candidate, especially the top candidates. Use at least four query families:
     - core topic phrase;
     - topic + "empirical evidence";
     - topic + "theory mechanism";
     - topic + "causal identification" or the expected design, e.g. DID, IV, DML.
   - Ensure recent literature is represented, especially the last two years when the topic is current or policy-driven.
   - If MCP tools are unavailable, use the bundled fallback:

```bash
python path/to/topic-feasibility-screener/scripts/literature_probe.py --topic "ROUGH_TOPIC" --terms VAR1 VAR2 MECHANISM --outdir "OUTPUT_DIR/literature"
```

   - If fallback search reports API errors or no valid records, do not conclude that no literature exists. Retry with `$nature-academic-search`, CrossRef, Semantic Scholar, Google Scholar, publisher pages or broader keywords.
   - Judge whether the topic has:
     - a clear research question;
     - a literature gap or unresolved tension;
     - a plausible mechanism;
     - a contribution beyond merely changing the sample;
     - a defensible boundary condition.

   - For top candidates, report literature density, recent 2024+ coverage, theory support, and whether the gap is too crowded, usable or too thin.

4. **Inspect the data.**
   - Identify rows, columns, missingness, numeric variables, likely identifiers and time variables.
   - Classify variables into rough roles: outcome, treatment/key variable, control, group/dummy, id, time or other.
   - Do not infer variable meaning from names alone when the name is ambiguous. Flag ambiguity.

5. **Run the visual research-topic lab.**
   - Default to `scripts/research_topic_lab.py`; use the older `scripts/screen_topics.py` only for a very fast minimal check.
   - For CSV/DTA:

```bash
python path/to/topic-feasibility-screener/scripts/research_topic_lab.py "DATA_PATH" --topic "ROUGH_TOPIC"
```

   - If the user gives specific variables:

```bash
python path/to/topic-feasibility-screener/scripts/research_topic_lab.py "DATA_PATH" --topic "ROUGH_TOPIC" --y Y1 Y2 --x X1 X2 --controls C1 C2 C3 --id firm_id --time year
```

6. **Read the generated outputs.**
   - `research_topic_lab_report.html`: main visual dashboard with score charts, top-topic cards, ranked topic table, literature evidence, external-data expansion and second-pass validation.
   - `feature_validation_checks.csv`: mandatory self-audit for data reading, brainstorming breadth, literature diagnostics, strict literature scoring, second-pass validation and chart links. Read this before trusting the report; any `passed = False` item must be fixed or disclosed.
   - `topic_scores.csv`: integrated theory/data scores for candidate topics.
   - `second_pass_validation.csv`: deeper checks for the top three topics.
   - `literature_evidence.csv`: real literature metadata used by the scoring.
   - `external_data_profile.csv`: root-directory datasets scanned for additional outcomes, mechanisms, moderators and merge possibilities.
   - `external_topic_ideas.csv`: topic-expansion ideas generated from external datasets.
   - `variable_profile.csv`: variable types, missingness, distribution and role hints.
   - `summary.json`: machine-readable summary.

7. **Synthesize into a research plan.**
   - Give 8-20 candidate topic directions, grouped by likely design:
     - baseline association or panel FE
     - DID or event study if treatment and time are present
     - mechanism tests if mediator-like variables exist
     - heterogeneity tests if group variables exist
     - robustness or alternative outcomes if multiple outcome dimensions exist
   - For each candidate, report:
     - dependent variable
     - key explanatory/treatment variable
     - minimal result: coefficient, p-value, usable N
     - literature support: dense, active/usable, thin-to-moderate or too thin
     - theory gap feasibility score
     - theory support score
     - empirical feasibility score
     - integrated overall score
     - second-pass validation outcome for the top three
     - identification work still needed
     - feasibility label: A-level, B-level, C-level or reject/backup

## Minimal Verification Standards

Use these standards when judging candidate topics. A topic should pass both theory and data gates.

### Theory Gate

- **Clear question:** the independent variable, outcome and setting can be stated in one sentence.
- **Literature gap:** prior work exists, but the exact mechanism, setting, outcome or identification remains unresolved.
- **Mechanism:** at least one plausible channel links treatment to outcome.
- **Boundary:** the claim is scoped to a period, industry, country, policy regime or firm type.
- **Novelty risk:** if the literature is too dense, require a sharper mechanism or design; if too thin, require stronger theory and data validation.

### Data Gate

- **Promising:** p < 0.05, adequate sample size, interpretable variable roles, and a plausible causal or theoretical story.
- **Borderline:** 0.05 <= p < 0.10 or limited sample size, but theory and design are credible.
- **Weak:** p >= 0.10, unstable sign, severe missingness, or unclear variable meaning.
- **Not recommended:** no variation, too few observations, impossible timing, obvious reverse causality with no design, or variables that cannot be explained.

### Combined Feasibility Labels

- **A-level candidate:** integrated score >= 82, clear literature gap, plausible mechanism, usable identification design and strong first-pass empirical signal.
- **B-level candidate:** integrated score 68-81.9; theory is strong but initial p-value is marginal, or data signal is strong but mechanism/design needs sharpening.
- **C-level candidate:** integrated score 52-67.9; either theory or data is weak. Use only as backup.
- **Reject/backup:** integrated score < 52, no literature footing, no data variation, or no credible identification path.

### Integrated Scoring Model

Use a transparent weighted score rather than a single p-value:

- Empirical feasibility: based on both first-pass and second-pass validation. First-pass p-values are graded distinctly for 1%, 5%, 10%, 20% and insignificant results. For the top three topics, second-pass validation updates the empirical score using TWFE/FE significance, placebo/permutation evidence and DID pretrend diagnostics when applicable.
- Theory support: based on paper-level weighted evidence, not only literature counts. Each paper receives points for source tier, relevance to the candidate topic, recency, citations, mechanism content and identification/method content. Top journals and authoritative peer-reviewed journals add substantially more than low-signal or unknown sources.
- Theory gap: highest when the literature is active but not saturated and when mechanism/identification anchors exist; lower when the topic is either too crowded or too thin.
- Topic alignment: keeps the candidate connected to the user's stated seed topic, while still allowing open brainstorming when no topic is supplied.
- Design bonus: add a small bonus for credible DID/event-study or panel-FE structure, but never let design labels substitute for actual diagnostics.

The current script follows design ideas observed in public GitHub research-agent skills and research-lab agents: research ideation should expand from datasets into questions, hypotheses, mechanisms, boundaries and identification strategies; literature review should use real metadata and quality filters rather than hit counts; data discovery should score datasets by merge keys, variables, coverage and limitations; and the final output should be a visual, inspectable report rather than a raw spreadsheet dump.

### Granular Literature Scoring

Do not let all candidates in the same broad topic receive the same theory scores. The script must score papers and then aggregate by candidate:

- **Search state first:** distinguish `searched`, `not searched`, `rate_limited`, `searched_insufficient_relevance` and `search_error`. Missing/failed searches must display as `NA`, not as zero-valued evidence.
- **Provider diagnostics:** record the provider (`OpenAlex`, `CrossRef`, or other fallback), query family, raw hits, valid hits, relevant hits and error message for every query. Never hide HTTP 429/rate-limit failures.
- **Wide search, strict scoring:** broad queries can populate the evidence table, but theory scores should use only papers passing relevance and evidence-class screens.
- **Evidence class:** separate `direct`, `bridge`, `background` and `weak` evidence. Direct evidence must match both sides of the candidate relationship in the paper title/abstract/source, not in the search query and not only in the candidate title. Bridge evidence includes broader concept-cluster matches such as information assets, intellectual capital, intangible resources, data valuation, data disclosure, investor judgement and information environment. For exploratory topic screening, `direct = 0` with dense bridge evidence should be treated as a potential research gap rather than an automatic weakness.
- **Source tier:** use coarse 0-100 display bands rather than false precision: top journals = 100, strong peer-reviewed journals = 75, ordinary journal articles = 50, and SSRN/books/chapters/manual-check sources = 25. Preprints can still contribute as frontier evidence when recent and conceptually relevant, but they must not be counted as peer-reviewed/top-tier hits.
- **Relevance:** title, abstract and query terms must match the candidate's treatment, outcome and themes. A directly relevant ordinary journal can outrank an unrelated top journal.
- **Recency:** 2024+ papers add points for active/current topics, especially policy-driven topics.
- **Citation signal:** use a log citation score so old high-citation papers help without overwhelming the score.
- **Mechanism evidence:** add points when abstracts discuss channels such as information asymmetry, disclosure, governance, audit quality, analysts, financing or reputation.
- **Identification evidence:** add points for causal methods such as DID, event study, IV, panel FE, DML or matching.
- **Query coverage:** record how many query families produced useful hits; a candidate supported by only one broad query is weaker than one supported across mechanism, empirical and identification queries.
- **Innovation gap logic:** when direct evidence is absent but bridge evidence is dense, create or raise `innovation_gap_score`. This distinguishes “no theory footing” from “no one has directly studied this yet, but adjacent literatures can support a credible contribution.”

Display `literature_search_state`, `raw_literature_hits`, `relevant_literature_hits`, `direct_evidence_hits`, `background_evidence_hits`, `mean_paper_quality`, `mean_relevance`, `query_families_with_hits`, `top_tier_hits`, `peer_reviewed_hits`, `method_hits` and `mechanism_hits` in the report.

## Recommended Empirical Escalation

After minimal screening, automatically run second-pass validation for the top three topics:

- **DID/event study:** when treatment, entity and time structure exist, run a TWFE check, event-study/pretrend check and placebo/permutation-style validation. Treat parallel-trend tests as diagnostic, not proof, because low power is common.
- **Panel fixed effects:** when entity and time variables exist but treatment timing is unclear, run two-way fixed effects and placebo/shuffled-key-variable validation.
- **Pooled/cross-sectional model:** run robust OLS plus shuffled-key-variable placebo. Recommend stronger designs such as lag structure, IV, matching, mechanism tests or alternative outcomes only if theory supports them.
- **Mechanism test:** use only mediators that are theoretically downstream of the treatment and not mechanically identical to the outcome.
- **Heterogeneity:** use pre-determined or pre-policy group variables. Avoid post-treatment grouping.
- **IV:** require an exclusion story and first-stage relevance. Do not invent IVs purely from significance.
- **DML/DDML:** suggest when many controls or nonlinear selection concerns exist, but keep a transparent baseline model.

## Visualization Requirements

The primary output must be `research_topic_lab_report.html`. It should include:

- ranked top-topic cards with theory gap, mechanism and score components;
- clickable chart cards linking to standalone chart HTML files under `charts/`; verify those files exist and open;
- an overall score bar chart;
- a theory-vs-empirical scatter plot;
- a theory-component chart comparing support and gap scores;
- an empirical-component chart comparing first-pass and second-pass scores;
- an external-data theme chart when a root directory is scanned;
- tables for ranked topics, second-pass validation, literature evidence, literature query diagnostics, external-data expansion ideas and variable profiles.

Do not treat CSV/XLSX output as the deliverable. Those files are audit trails behind the visual report.

## Mandatory Feature Verification

After every run, open `feature_validation_checks.csv` and confirm every row passes:

- `data_reading`: dataset loaded and variable profile generated.
- `topic_brainstorming`: enough candidate topics, outcomes and key variables were generated; otherwise broaden variable-role rules or external data scanning.
- `external_data_expansion`: root-directory files were scanned when available.
- `literature_search_diagnostics`: queries ran or a skipped/rate-limited state is explicit.
- `literature_strict_scoring`: evidence rows include `source_type` and `evidence_class`, separating direct, bridge, background and weak evidence.
- `second_pass_validation`: top-topic validation ran.
- `visual_dashboard_links`: standalone chart pages exist under `charts/`.
- `direct_zero_gap_logic`: candidates without direct evidence are evaluated through bridge evidence and `innovation_gap_score`, not a hard support cap.

If any check fails, fix the script or clearly report the failed function. Do not present the dashboard as reliable while a required check is failing.

## Reporting Template

Use this structure in the final answer:

```markdown
**Data Read**
Loaded DATA with N observations and K variables. Detected firm id, time variable, likely outcomes and likely key variables.

**Visual Report**
- research_topic_lab_report.html: open this first. It contains score charts, ranked topic tables, literature evidence and top-three second-pass validation.

**Best Topic Directions**
1. Topic title
   - Literature feasibility:
   - Theory gap score / theory support score:
   - Empirical score / overall score:
   - Minimal result: coef = ..., p = ..., N = ...
   - Second-pass validation:
   - Identification still needed:
   - Overall feasibility:

**Not Recommended**
- Variable pair or topic, reason.

**Files Created**
- research_topic_lab_report.html
- feature_validation_checks.csv
- topic_scores.csv
- second_pass_validation.csv
- literature_evidence.csv
- external_data_profile.csv
- external_topic_ideas.csv
- variable_profile.csv
```

## Guardrails

- Do not promise publishability.
- Do not call a correlation "causal".
- Do not hide insignificant or contradictory results.
- Do not call a topic theoretically feasible only because papers exist. Explain the gap.
- Do not call a topic data-feasible only because variables exist. Check variation, missingness and usable N.
- Do not keep trying arbitrary transformations until significance appears unless the user explicitly asks for exploratory feature search, and even then label it exploratory.
- If the top result is substantively nonsensical, say so and demote it.
