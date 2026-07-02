---
name: topic-feasibility-screener
description: Screen CSV or Stata DTA datasets and academic literature for feasible empirical research topics. Use when the user gives a dataset and a rough paper idea, asks whether a topic is theoretically and empirically viable, wants many possible topic directions from existing data, or wants minimal code-based significance checks plus literature-gap validation before committing to a thesis, finance/accounting/economics/management paper, DID design, mechanism test, robustness test, or variable pairing.
---

# Topic Feasibility Screener

Use this skill to turn a rough empirical idea plus a `.csv` or `.dta` dataset into a first-pass topic feasibility report. The skill proposes candidate research directions from observed variables, runs minimal significance checks and probes the literature to judge whether a topic is both theoretically plausible and data-feasible.

## Core Stance

- Treat significance as a screening signal, not as proof of a publishable causal effect.
- Prefer theory-first topics with credible identification, usable variation, sufficient observations, interpretable variable definitions and defensible data sources.
- Require two forms of feasibility before recommending a topic: literature/theory feasibility and data/model feasibility.
- Never recommend a topic only because one p-value is small. Always state what identification design is still needed.
- Do not rename raw data columns unless the user asks. Use publication-style display names in reports and keep raw variable names in scripts.
- If the dataset contains sensitive or private data, avoid exposing raw rows in the response. Summarize variable names, counts and model outputs.

## Workflow

1. **Clarify the minimal input.**
   - Required: path to one `.csv` or `.dta`.
   - Helpful: rough topic phrase, e.g. "data-resource recognition and reputation", "digital finance and common prosperity", "ESG and financing constraints".
   - Optional: user-specified outcome variables, key explanatory variables, controls, firm identifier and time variable.

2. **Probe the literature and theory.**
   - If `$nature-academic-search` or academic-search MCP tools are available, use them first for multi-source searches.
   - Search at least four query families:
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

3. **Inspect the data.**
   - Identify rows, columns, missingness, numeric variables, likely identifiers and time variables.
   - Classify variables into rough roles: outcome, treatment/key variable, control, group/dummy, id, time or other.
   - Do not infer variable meaning from names alone when the name is ambiguous. Flag ambiguity.

4. **Run the bundled data screener.**
   - Use `scripts/screen_topics.py` unless the user asks for custom Stata/R code.
   - For CSV/DTA:

```bash
python path/to/topic-feasibility-screener/scripts/screen_topics.py "DATA_PATH" --topic "ROUGH_TOPIC" --json
```

   - If the user gives specific variables:

```bash
python path/to/topic-feasibility-screener/scripts/screen_topics.py "DATA_PATH" --topic "ROUGH_TOPIC" --y Y1 Y2 --x X1 X2 --controls C1 C2 C3 --id firm_id --time year --json
```

5. **Read the generated outputs.**
   - `variable_profile.csv`: variable types, missingness, distribution and role hints.
   - `candidate_models.csv`: minimal regressions, robust SEs, p-values, usable N and ranked scores.
   - `topic_screening_report.md`: human-readable topic directions and cautions.
   - `summary.json`: optional machine-readable summary.
   - `literature_probe.csv` / `literature_probe_report.md`: quick literature-density and recency evidence when fallback search is used.

6. **Synthesize into a research plan.**
   - Give 5-15 candidate topic directions, grouped by likely design:
     - baseline association or panel FE
     - DID or event study if treatment and time are present
     - mechanism tests if mediator-like variables exist
     - heterogeneity tests if group variables exist
     - robustness or alternative outcomes if multiple outcome dimensions exist
   - For each candidate, report:
     - dependent variable
     - key explanatory/treatment variable
     - minimal result: coefficient, p-value, usable N
     - literature support: dense, moderate, thin or absent
     - why the topic is theoretically plausible
     - what identification work remains
     - feasibility label: promising, borderline, weak, or not recommended

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

- **A-level candidate:** clear literature gap, plausible mechanism, usable identification design and p < 0.05 in a minimal model.
- **B-level candidate:** theory is strong but initial p-value is marginal, or data signal is strong but mechanism needs sharpening.
- **C-level candidate:** either theory or data is weak; use only as backup.
- **Reject for now:** no literature footing, no data variation, or no credible identification path.

## Recommended Empirical Escalation

After minimal screening, recommend the next design only when supported by the data structure:

- **Panel fixed effects:** firm/entity id and time variable exist.
- **DID:** treatment indicator, post-policy timing and treated/control variation exist.
- **Event study:** at least two pre-periods and one or more post-periods exist.
- **Mechanism test:** plausible mediator variables exist and are not mechanically identical to treatment or outcome.
- **Heterogeneity:** pre-determined group variables exist.
- **IV:** candidate instrument has theory, relevance and plausible exclusion. Do not invent IVs purely from significance.
- **DML/DDML:** many controls or nonlinear selection concerns exist, but still report the plain model first.

## Reporting Template

Use this structure in the final answer:

```markdown
**Data Read**
Loaded DATA with N observations and K variables. Detected firm id, time variable, likely outcomes and likely key variables.

**Best Topic Directions**
1. Topic title
   - Literature feasibility:
   - Minimal result: coef = ..., p = ..., N = ...
   - Why it is plausible:
   - Identification still needed:
   - Overall feasibility:

**Not Recommended**
- Variable pair or topic, reason.

**Files Created**
- topic_screening_report.md
- candidate_models.csv
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
