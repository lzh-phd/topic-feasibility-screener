# Topic Feasibility Screener

**First updated version / 第一次更新版**

`topic-feasibility-screener` is a Codex skill for screening empirical research topics from existing `.csv` or Stata `.dta` datasets. It combines dataset profiling, broad topic brainstorming, real literature search, transparent theory/data scoring, and second-pass validation into a visual HTML dashboard.

This version is designed for early-stage thesis and paper development in accounting, finance, economics, management, corporate governance, digital transformation, ESG, audit, disclosure, and capital-market research.

## What Is New In The First Updated Version

- Visual HTML dashboard as the main output, not a spreadsheet-only workflow.
- Broader topic brainstorming from all usable variables and nearby datasets.
- Literature search diagnostics with query family, provider status, raw hits, valid hits, relevant hits, and error messages.
- Transparent 0-100 score display for overall feasibility, empirical feasibility, theory support, theory gap, topic alignment, paper relevance, source tier, and innovation-gap value.
- Evidence classification into `direct`, `bridge`, `background`, and `weak`.
- Bridge literature is now treated as theoretically valuable when direct evidence is absent.
- `evidence_profile` explains whether a topic has direct evidence, bridge support, one-sided background support, or weak theoretical footing.
- Top-three second-pass validation, including fixed-effect checks and placebo/permutation-style diagnostics where the data structure allows.
- Mandatory self-audit file (`feature_validation_checks.csv`) to verify data reading, brainstorming, literature diagnostics, evidence scoring, second-pass validation, and chart links.

## Core Idea

The skill does not treat a significant coefficient as a publishable result. It screens whether a research topic has both:

1. **Theory feasibility**: a clear research question, adjacent literature, a plausible mechanism, and a credible research gap.
2. **Data feasibility**: usable variables, variation, sample size, interpretable roles, and a minimal empirical signal.

The first updated version explicitly separates two situations that older keyword-only tools often confuse:

- **No theory footing**: little or no relevant literature appears.
- **Potential frontier gap**: no paper directly studies the exact relationship, but adjacent literatures provide bridge evidence.

This is important for exploratory research. A topic with `direct_evidence_hits = 0` can still be promising if bridge evidence is dense and conceptually close.

## Main Script

Use the visual research-topic lab:

```powershell
python scripts\research_topic_lab.py "path\to\data.dta" --topic "data resource recognition and corporate reputation"
```

With specified variables:

```powershell
python scripts\research_topic_lab.py "path\to\data.dta" `
  --topic "data resource recognition and corporate reputation" `
  --y ReputationScore `
  --x entry `
  --controls Size Lev ROA Growth BM Board Indep Top1 SOE Cashflow Loss `
  --id firm_id `
  --time year
```

With root-directory scanning for additional datasets:

```powershell
python scripts\research_topic_lab.py "path\to\data.dta" `
  --topic "data resource recognition and corporate reputation" `
  --scan-root "path\to\project_folder" `
  --literature-top 30 `
  --per-query 8 `
  --deep-top 3 `
  --placebo-reps 200
```

## Outputs

The main output is:

- `research_topic_lab_report.html`

Supporting audit files include:

- `feature_validation_checks.csv`
- `topic_scores.csv`
- `second_pass_validation.csv`
- `literature_evidence.csv`
- `literature_query_diagnostics.csv`
- `external_data_profile.csv`
- `external_topic_ideas.csv`
- `variable_profile.csv`
- `summary.json`

Standalone chart pages are written under:

- `charts/`

## Scoring Overview

All major dashboard scores are displayed on a 0-100 scale.

- **Empirical score**: first-pass regression signal plus second-pass validation for top topics.
- **Theory support score**: paper-level evidence from source tier, relevance, recency, citations, method signals, mechanism signals, and evidence class.
- **Theory gap score**: rewards active but not saturated literatures and raises gap value when direct evidence is missing but bridge evidence is strong.
- **Topic alignment score**: keeps generated topics connected to the user's rough idea while still allowing broad brainstorming.
- **Innovation gap score**: separates a genuine theory vacuum from a frontier gap supported by adjacent literatures.

Evidence classes:

- `direct`: both sides of the candidate relationship appear in the paper text.
- `bridge`: adjacent concepts support the theoretical link, such as information assets, intellectual capital, intangible resources, data valuation, data disclosure, investor judgment, or information environment.
- `background`: useful one-sided or contextual evidence.
- `weak`: low relevance or insufficient anchors.

## Guardrails

- Do not treat screening significance as causal proof.
- Do not call a topic publishable only because the dashboard ranks it highly.
- Check `feature_validation_checks.csv` before trusting the report.
- Review `literature_evidence.csv` and `literature_query_diagnostics.csv` before relying on theory scores.
- Use manual academic judgment for final variable definitions, identification design, sample restrictions, and literature positioning.

## Installation

Copy this folder into your Codex skills directory:

```powershell
C:\Users\<you>\.codex\skills\topic-feasibility-screener
```

Then invoke it in Codex:

```text
[$topic-feasibility-screener] Here is my DTA/CSV. The rough topic is digital transformation and financing constraints. Please screen feasible topics and run minimal validation.
```

## License

MIT License.
