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

## Design Upgrade Checklist

### Panel FE

Use when entity and time identifiers exist. Check whether key variables vary within entity over time.

### DID

Use when treatment timing is observable. Require:

- treated and control groups;
- pre- and post-treatment observations;
- no obvious anticipation;
- event-study or pre-trend check.

### Mechanism

Use when the mediator is theoretically downstream of treatment and upstream of outcome. Do not use a variable that is mechanically constructed from the outcome.

### Heterogeneity

Use pre-determined or pre-policy grouping variables. Avoid post-treatment groups.

### IV

Use only when there is a credible exclusion story. First-stage significance is necessary but not sufficient.

### DML/DDML

Use as a robustness or selection-adjustment tool when there are many controls or nonlinear selection concerns. Keep a transparent baseline model.

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
