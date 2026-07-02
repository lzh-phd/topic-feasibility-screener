# Topic Feasibility Screener

`topic-feasibility-screener` is a Codex skill for screening empirical research topics from existing `.csv` or Stata `.dta` datasets. It combines two checks:

1. **Theory and literature feasibility**: whether the topic has a clear research question, literature gap, plausible mechanism and defensible boundary.
2. **Data feasibility**: whether the dataset contains usable outcomes, key variables, controls, variation and enough observations for a minimal empirical test.

The skill is designed for early-stage thesis, accounting, finance, economics and management paper development. It helps prioritize topics before committing to a full empirical design.

## What It Does

- Reads `.csv` and `.dta` files.
- Profiles variables, missingness, distributions and likely roles.
- Detects candidate outcomes, treatment/key variables, controls, identifiers and time variables.
- Runs minimal OLS-style screening models with robust standard errors.
- Ranks candidate topic directions by statistical signal and feasibility.
- Probes literature density and recency through an OpenAlex fallback script.
- Produces Markdown and CSV reports for review.

## Installation

Copy this folder into your Codex skills directory:

```powershell
C:\Users\<you>\.codex\skills\topic-feasibility-screener
```

Then invoke it in Codex:

```text
[$topic-feasibility-screener] Here is my DTA/CSV. The rough topic is digital transformation and financing constraints. Please screen feasible topics and run minimal validation.
```

## Script Usage

Run the data screener directly:

```powershell
python scripts\screen_topics.py "path\to\data.dta" --topic "data-resource recognition and corporate reputation" --json
```

With specified variables:

```powershell
python scripts\screen_topics.py "path\to\data.dta" `
  --topic "data-resource recognition and corporate reputation" `
  --y ReputationScore `
  --x entry `
  --controls Size Lev ROA Growth BM Board Indep Top1 SOE Cashflow Loss `
  --id firm_id `
  --time year `
  --json
```

Run the literature fallback probe:

```powershell
python scripts\literature_probe.py `
  --topic "data resource recognition corporate reputation" `
  --terms "data assets" "accounting recognition" "corporate reputation" `
  --outdir ".\literature_probe"
```

## Outputs

The data screener creates:

- `variable_profile.csv`
- `candidate_models.csv`
- `topic_screening_report.md`
- `summary.json` when `--json` is used

The literature probe creates:

- `literature_probe.csv`
- `literature_probe_report.md`
- `literature_probe_summary.json`

## Guardrails

This skill is for topic screening, not final causal inference.

- A significant coefficient is not proof of causality.
- A topic is not feasible unless both theory and data are plausible.
- DID, IV, mechanism and DML designs still require separate identification checks.
- Literature-search failures should not be interpreted as absence of literature. Use CrossRef, Semantic Scholar, Google Scholar or a dedicated academic-search workflow for final verification.

## License

MIT License.
