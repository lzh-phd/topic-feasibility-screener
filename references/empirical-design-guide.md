# Empirical Design Guide

Use this reference only when the screening report needs deeper interpretation.

## Topic Feasibility Signals

Strong empirical topic candidates usually have:

- a dependent variable that is meaningful and measurable;
- a key explanatory variable with variation across firms and time;
- enough non-missing observations after controls;
- a plausible direction from theory;
- a design that can address selection or reverse causality;
- clean data-source wording that a reviewer would accept.

## Brainstorming Requirements

Do not restrict candidate topics to the user's first phrase. Treat the phrase as a seed. A good screener should expand in four directions:

1. **Outcome expansion:** identify all credible dependent variables in the dataset, including reputation, financing constraints, performance, risk, analyst behavior, audit outcomes, innovation, trading activity and textual disclosure.
2. **Treatment/key-variable expansion:** identify policy, recognition, digital, ESG, governance, audit, disclosure, ownership or shock variables that could plausibly explain outcomes.
3. **Mechanism expansion:** identify mediator-like variables that sit between the key variable and the outcome. Reject variables that are mechanically identical to the treatment or outcome.
4. **Boundary expansion:** identify pre-determined groups for heterogeneity, such as ownership, industry, region, audit quality, pre-policy disclosure, firm size or governance quality.

For every candidate topic, force a one-sentence structure:

`In [sample/setting], does [key variable/treatment] affect [outcome], through [mechanism], under [identification design]?`

If the mechanism or identification design cannot be stated, the topic can still be screened but should not be labelled A-level.

## Theory Feasibility Checklist

A topic is theoretically feasible only when these five elements can be stated clearly:

1. **Phenomenon:** what relationship or effect is being studied.
2. **Gap:** what prior literature has not resolved.
3. **Mechanism:** why the effect should exist and through which channel.
4. **Scope:** where the claim holds, such as country, sample, period, policy or industry.
5. **Contribution:** what the paper adds beyond changing the dataset.

Use literature search to classify the gap:

- **Dense literature:** many recent papers exist. Feasibility depends on a sharper mechanism, better identification or a new institutional setting.
- **Moderate literature:** enough references exist to anchor the paper. Feasibility is usually good if the data signal is credible.
- **Thin literature:** potential novelty exists, but framing burden is high. Require stronger theory and more careful validation.
- **No literature:** do not proceed unless the user can supply domain evidence or institutional facts.

### Theory Support Scoring

Use real literature metadata rather than invented references. Score theory support as:

- Report search state before reporting scores. If a source is rate-limited, unavailable, skipped or outside the literature-search budget, show `NA` for theory scores rather than zero. Zero is evidence only when a successful search found no relevant records.
- Use more than one provider when possible. OpenAlex is preferred for broad metadata; CrossRef is a fallback when OpenAlex is rate-limited or returns no records. Keep provider-level diagnostics.
- Store query diagnostics: provider, query family, raw hits, valid hits, relevant hits, status and error message.
- Classify evidence as direct, background or weak. Direct evidence must match both the treatment/key construct and the outcome/theoretical construct in the paper title, abstract or source, not merely in the query string.
- Score each paper, then aggregate. Do not assign the same support score to all topics in the same broad field.
- Paper-level points should include source tier, relevance, recency, citations, mechanism evidence and identification/method evidence.
- Top journals or field-leading journals receive the largest base score; ordinary indexed journals receive moderate points; working papers, preprints and unknown sources receive small points unless they are highly relevant and cited.
- A few directly relevant top-tier or high-quality papers can outweigh many weakly related papers.
- Recent 2024+ papers should increase support when the topic is current, but recency alone should not dominate quality.

Indicative bands:

- 85-100: high-quality literature with top/strong journal support, recent papers, and clear mechanism or identification anchors.
- 70-84: active literature with usable anchors, but the exact mechanism/outcome/design remains underdeveloped.
- 50-69: thin-to-moderate literature. Novelty may exist, but framing requires careful theory.
- below 50: too little reliable literature, low-quality sources, or search failure. Re-search before recommending.

### Theory Gap Scoring

The best gap is neither empty nor saturated:

- Highest: moderate/active literature with unresolved mechanism, setting, measurement or identification.
- Lower: very dense literature unless the topic has a clearly sharper design or new institutional shock.
- Lower: very thin literature unless the user supplies strong institutional facts.

## Data Feasibility Checklist

A topic is data-feasible only when the dataset contains:

- a measurable dependent variable;
- a key explanatory or treatment variable with non-trivial variation;
- enough observations after missing-value filtering;
- plausible controls or fixed effects;
- time information if the design needs pre/post tests;
- treated and control groups if the design is DID;
- mechanism variables if a mechanism claim will be made;
- variable definitions and data-source provenance.

Minimum red flags:

- treatment group is extremely small;
- no pre-treatment period for DID;
- outcome or treatment has no variation;
- more than half the sample is lost after basic controls;
- the top significant relationship is mechanically constructed;
- the theoretical direction contradicts the sign and no explanation is available.

### Empirical Feasibility Scoring

Score empirical feasibility using:

- coefficient significance and stability, with distinct scores for 1%, 5%, 10%, 20% and insignificant results;
- usable observations after controls;
- treatment/key-variable variation;
- panel structure and within-firm variation;
- availability of controls, fixed effects and pre/post timing;
- whether deeper checks can be run.

Never let a single p-value dominate the score. A significant but mechanically constructed relationship should be demoted.

For the top three candidates, replace or supplement the first-pass empirical score with a second-pass score:

- DID/event-study candidates: TWFE/DID p-value, placebo/permutation p-value, and pretrend diagnostic.
- Panel FE candidates: two-way fixed-effects p-value and shuffled-treatment placebo.
- Pooled candidates: robust OLS p-value and shuffled-key-variable placebo.

The final empirical score should report both components: first-pass empirical score and second-pass score.

Use significance levels explicitly in empirical scoring:

- p < 0.01: strong first-pass signal.
- 0.01 <= p < 0.05: good signal.
- 0.05 <= p < 0.10: borderline but usable if theory/design are strong.
- 0.10 <= p < 0.20: exploratory only.
- p >= 0.20: weak unless the task is pure diagnostics.

For top candidates, second-pass evidence should remain visible separately from the final blended empirical score. Do not hide that a topic passed first-pass screening but failed placebo or pretrend diagnostics.

## External Data Expansion

When the workspace root contains additional datasets, profile them automatically instead of relying only on the user-provided panel.

Classify each external dataset by:

- likely firm identifier and time variables;
- merge readiness;
- candidate outcomes;
- candidate treatments or moderators;
- candidate controls;
- dominant themes;
- limitations or missing merge keys.

Use merge-ready files as possible sources of additional outcomes, mechanisms, heterogeneity variables and robustness tests. Use non-merge-ready files only as conceptual prompts until a valid linkage strategy is confirmed.

When many additional datasets are available, expand the topic space through six lenses rather than only matching the user's seed variables:

1. **Main effect:** a new treatment/key variable explains an economically meaningful outcome.
2. **Mechanism:** a mediator explains why the baseline effect occurs.
3. **Economic consequence:** a downstream outcome shows what the baseline effect leads to.
4. **Heterogeneity:** a predetermined group identifies where the effect is stronger.
5. **Robustness:** an alternative measurement of the same construct tests whether the story is stable.
6. **Identification:** a policy shock, event, instrument, DDD dimension or matching variable strengthens the design.

For each external variable idea, report an ideation lens, theory anchor and required data action. A merge-ready dataset should say "left-merge by firm id and year"; a non-merge-ready dataset should say what linkage must be checked before modeling.

## Design Upgrade Checklist

### Panel FE

Use when entity and time identifiers exist. Check whether key variables vary within entity over time.

### DID

Use when treatment timing is observable. Require:

- treated and control groups;
- pre- and post-treatment observations;
- no obvious anticipation;
- event-study or pre-trend check.

Second-pass DID validation should include:

- TWFE estimate or comparable DID estimate;
- event-study coefficients with at least two pre-periods if available;
- pretrend diagnostic, clearly labelled as diagnostic rather than proof;
- placebo or permutation-style check by shuffling treatment or treatment timing;
- treated/control counts and pre/post support.

If pre-periods are insufficient, report that DID is under-validated and suggest panel FE or another design instead.

### Mechanism

Use when the mediator is theoretically downstream of treatment and upstream of outcome. Do not use a variable that is mechanically constructed from the outcome.

Second-pass mechanism validation should include:

- treatment to mediator;
- treatment to outcome;
- outcome regression including treatment and mediator only as descriptive support;
- timing check when lags are available;
- warning if mediator and outcome are contemporaneous.

### Heterogeneity

Use pre-determined or pre-policy grouping variables. Avoid post-treatment groups.

### IV

Use only when there is a credible exclusion story. First-stage significance is necessary but not sufficient.

Second-pass IV validation should include:

- first-stage coefficient and F-statistic;
- reduced form;
- direct association between instrument and outcome after controlling for treatment where meaningful;
- a written exclusion-restriction risk analysis.

### DML/DDML

Use as a robustness or selection-adjustment tool when there are many controls or nonlinear selection concerns. Keep a transparent baseline model.

Second-pass DML/DDML validation should include:

- a transparent baseline result;
- cross-fitting description;
- at least one learner-replacement check when feasible;
- comparison of signs and magnitudes across baseline and DML results.

## Variable Display Names

For paper tables, use readable empirical names rather than raw code names:

- `Rep`: corporate reputation score
- `DRR`: data-resource recognition
- `SA`: SA financing-constraint index
- `AbsDA`: absolute discretionary accruals
- `CFO`: operating cash flow
- `ListAge`: listing age
- `FirmAge`: firm age
- `Return`: annual stock return

Raw column names can remain in code if changing them would break reproducibility.
