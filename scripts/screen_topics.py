#!/usr/bin/env python
"""Screen a CSV/DTA dataset for feasible empirical research topics.

The script is intentionally conservative: it proposes candidate relationships
from observed data structure and runs minimal checks, but it never claims causal
identification from significance alone.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ID_PATTERNS = re.compile(r"(id|code|stkcd|permno|cusip|证券|股票|代码|公司)", re.I)
TIME_PATTERNS = re.compile(r"(year|yr|date|time|month|quarter|qtr|年份|年度|日期|季度)", re.I)
OUTCOME_PATTERNS = re.compile(
    r"(score|reputation|rep|q|roa|roe|risk|crash|turnover|return|ret|growth|"
    r"innovation|patent|constraint|sa|ww|kz|em|da|absda|analyst|forecast|"
    r"声誉|风险|崩盘|换手|收益|增长|创新|专利|融资|约束|盈余|分析师|预测|分歧)",
    re.I,
)
TREAT_PATTERNS = re.compile(
    r"(treat|post|did|entry|policy|pilot|shock|dummy|high|digital|data|"
    r"recognition|disclosure|iv|instrument|入表|政策|试点|处理|冲击|数字|数据|披露|高)",
    re.I,
)
CONTROL_PATTERNS = re.compile(
    r"(size|lev|roa|roe|growth|bm|tobinq|board|indep|top1|soe|cash|cfo|loss|age|ato|"
    r"资产|负债|盈利|成长|账面|市值|董事|独董|股权|国企|现金流|亏损|年龄|周转)",
    re.I,
)


@dataclass
class VarInfo:
    name: str
    dtype: str
    n: int
    missing_rate: float
    unique: int
    mean: float | None
    std: float | None
    min: float | None
    max: float | None
    role_hint: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", help="Input .csv or .dta file")
    parser.add_argument("--topic", default="", help="Short description of the intended topic")
    parser.add_argument("--outdir", default=None, help="Output directory")
    parser.add_argument("--max-models", type=int, default=80, help="Maximum candidate models to estimate")
    parser.add_argument("--top", type=int, default=20, help="Number of ranked candidates to report")
    parser.add_argument("--min-n", type=int, default=100, help="Minimum usable observations per model")
    parser.add_argument("--y", nargs="*", default=None, help="Optional candidate outcome variables")
    parser.add_argument("--x", nargs="*", default=None, help="Optional candidate explanatory/treatment variables")
    parser.add_argument("--controls", nargs="*", default=None, help="Optional control variables")
    parser.add_argument("--id", default=None, help="Optional panel/entity identifier")
    parser.add_argument("--time", default=None, help="Optional time variable")
    parser.add_argument("--json", action="store_true", help="Also write machine-readable JSON summary")
    return parser.parse_args()


def load_data(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".dta":
        return pd.read_stata(path, convert_categoricals=False)
    raise SystemExit(f"Unsupported file type: {suffix}. Use .csv or .dta.")


def safe_num(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    if s.dtype == object:
        cleaned = s.astype(str).str.replace(",", "", regex=False)
        return pd.to_numeric(cleaned, errors="coerce")
    return pd.to_numeric(s, errors="coerce")


def role_hint(name: str, s: pd.Series, nrows: int) -> str:
    lname = str(name)
    nunique = s.nunique(dropna=True)
    numeric = pd.api.types.is_numeric_dtype(s) or safe_num(s).notna().mean() > 0.8
    if ID_PATTERNS.search(lname) and nunique > max(20, nrows * 0.1):
        return "id"
    if TIME_PATTERNS.search(lname):
        return "time"
    if numeric and TREAT_PATTERNS.search(lname) and nunique <= 20:
        return "treatment"
    if numeric and TREAT_PATTERNS.search(lname):
        return "key_x"
    if numeric and OUTCOME_PATTERNS.search(lname):
        return "outcome"
    if numeric and CONTROL_PATTERNS.search(lname):
        return "control"
    if numeric and 2 <= nunique <= 10:
        return "group_or_dummy"
    if numeric:
        return "numeric"
    return "other"


def profile_vars(df: pd.DataFrame) -> list[VarInfo]:
    rows: list[VarInfo] = []
    nrows = len(df)
    for col in df.columns:
        s = df[col]
        num = safe_num(s)
        numeric_share = num.notna().mean()
        numeric = numeric_share > 0.8
        rows.append(
            VarInfo(
                name=str(col),
                dtype=str(s.dtype),
                n=int(s.notna().sum()),
                missing_rate=float(s.isna().mean()),
                unique=int(s.nunique(dropna=True)),
                mean=float(num.mean()) if numeric else None,
                std=float(num.std()) if numeric else None,
                min=float(num.min()) if numeric else None,
                max=float(num.max()) if numeric else None,
                role_hint=role_hint(str(col), s, nrows),
            )
        )
    return rows


def choose_candidates(
    infos: list[VarInfo], args: argparse.Namespace
) -> tuple[list[str], list[str], list[str], str | None, str | None]:
    names = [v.name for v in infos]
    by_name = {v.name: v for v in infos}
    numeric_names = [v.name for v in infos if v.role_hint not in {"id", "time", "other"} and v.n >= args.min_n]

    y_vars = args.y or [v.name for v in infos if v.role_hint == "outcome"]
    if not y_vars:
        y_vars = [v.name for v in infos if v.role_hint == "numeric"][:8]

    x_vars = args.x or [v.name for v in infos if v.role_hint in {"treatment", "key_x", "group_or_dummy"}]
    if not x_vars:
        x_vars = [v.name for v in infos if v.role_hint == "numeric" and v.name not in y_vars][:10]

    controls = args.controls
    if controls is None:
        controls = [v.name for v in infos if v.role_hint == "control"]
        if len(controls) < 3:
            controls += [n for n in numeric_names if n not in set(y_vars + x_vars + controls)][:8]

    id_var = args.id or next((v.name for v in infos if v.role_hint == "id"), None)
    time_var = args.time or next((v.name for v in infos if v.role_hint == "time"), None)

    y_vars = [v for v in y_vars if v in by_name]
    x_vars = [v for v in x_vars if v in by_name and v not in y_vars]
    controls = [v for v in controls if v in by_name and v not in set(y_vars + x_vars)]
    return y_vars[:12], x_vars[:16], controls[:12], id_var, time_var


def standardize_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(name)).strip("_")[:48] or "var"


def make_design(df: pd.DataFrame, y: str, x: str, controls: list[str], time_var: str | None) -> tuple[pd.Series, pd.DataFrame]:
    cols = [y, x] + controls + ([time_var] if time_var else [])
    d = df[cols].copy()
    for col in [y, x] + controls:
        d[col] = safe_num(d[col])
    d = d.replace([np.inf, -np.inf], np.nan).dropna()
    yy = d[y]
    X_parts = [d[[x] + controls]]
    if time_var and time_var in d.columns and d[time_var].nunique(dropna=True) <= 30:
        fe = pd.get_dummies(d[time_var], prefix=standardize_name(time_var), drop_first=True, dtype=float)
        X_parts.append(fe)
    X = pd.concat(X_parts, axis=1)
    X.insert(0, "const", 1.0)
    return yy, X


def ols_hc1(yy: pd.Series, X: pd.DataFrame, x: str) -> dict | None:
    y_arr = yy.to_numpy(dtype=float).reshape(-1, 1)
    X_arr = X.to_numpy(dtype=float)
    n, k = X_arr.shape
    if n <= k + 1:
        return None
    xtx_inv = np.linalg.pinv(X_arr.T @ X_arr)
    beta = xtx_inv @ X_arr.T @ y_arr
    resid = y_arr - X_arr @ beta
    meat = X_arr.T @ ((resid.flatten() ** 2)[:, None] * X_arr)
    scale = n / max(n - k, 1)
    cov = scale * xtx_inv @ meat @ xtx_inv
    params = pd.Series(beta.flatten(), index=X.columns)
    se = pd.Series(np.sqrt(np.maximum(np.diag(cov), 0)), index=X.columns)
    y_mean = float(np.mean(y_arr))
    ssr = float(np.sum(resid ** 2))
    sst = float(np.sum((y_arr - y_mean) ** 2))
    r2 = 1 - ssr / sst if sst > 0 else np.nan
    coef = float(params[x])
    stderr = float(se[x])
    if stderr <= 0 or math.isnan(stderr):
        pval = np.nan
    else:
        z = abs(coef / stderr)
        pval = float(math.erfc(z / math.sqrt(2)))
    return {
        "coef": coef,
        "se": stderr,
        "p": pval,
        "r2": float(r2),
        "n": int(n),
        "effect_abs_t": abs(coef / stderr) if stderr and not math.isnan(stderr) else np.nan,
    }


def fit_model(df: pd.DataFrame, y: str, x: str, controls: list[str], time_var: str | None, min_n: int) -> dict | None:
    yy, X = make_design(df, y, x, controls, time_var)
    if len(yy) < min_n or x not in X.columns:
        return None
    if yy.nunique(dropna=True) < 5 or safe_num(X[x]).nunique(dropna=True) < 2:
        return None
    fitted = ols_hc1(yy, X, x)
    if fitted is None:
        return None
    return {
        "outcome": y,
        "key_variable": x,
        "controls": "; ".join(controls),
        "time_fe": bool(time_var),
        "n": fitted["n"],
        "coef": fitted["coef"],
        "se": fitted["se"],
        "p": fitted["p"],
        "r2": fitted["r2"],
        "effect_abs_t": fitted["effect_abs_t"],
    }


def score_candidate(row: dict) -> float:
    p = row.get("p", np.nan)
    n = row.get("n", 0)
    r2 = row.get("r2", 0)
    t = row.get("effect_abs_t", 0)
    if math.isnan(p):
        return -999
    sig = 4 if p < 0.01 else 3 if p < 0.05 else 2 if p < 0.1 else 0
    n_score = min(2, math.log10(max(n, 1)) / 2)
    r_score = min(1, max(0, r2))
    return sig * 2 + min(t, 5) + n_score + r_score


def topic_sentence(row: dict, topic: str) -> str:
    direction = "positive" if row["coef"] > 0 else "negative"
    base = f"Whether {row['key_variable']} has a {direction} association with {row['outcome']}"
    if topic:
        return f"{base} in the context of {topic}."
    return base + "."


def feasibility_label(row: dict) -> str:
    if row["n"] < 300:
        return "caution: small usable sample"
    if row["p"] < 0.05:
        return "promising"
    if row["p"] < 0.1:
        return "borderline"
    return "weak initial evidence"


def write_report(
    outdir: Path,
    data_path: Path,
    topic: str,
    infos: list[VarInfo],
    candidates: pd.DataFrame,
    y_vars: list[str],
    x_vars: list[str],
    controls: list[str],
    id_var: str | None,
    time_var: str | None,
    args: argparse.Namespace,
) -> None:
    top = candidates.head(args.top).copy()
    lines: list[str] = []
    lines.append("# Topic feasibility screening report")
    lines.append("")
    lines.append(f"Input data: `{data_path}`")
    lines.append(f"Approximate topic: {topic or 'not specified'}")
    max_n = max((v.n for v in infos), default=0)
    lines.append(f"Observations: approximately {max_n:,}; variables profiled: {len(infos):,}.")
    lines.append("")
    lines.append("## Detected structure")
    lines.append("")
    lines.append(f"- Candidate outcomes: {', '.join(y_vars) or 'none detected'}")
    lines.append(f"- Candidate key variables: {', '.join(x_vars) or 'none detected'}")
    lines.append(f"- Candidate controls: {', '.join(controls) or 'none detected'}")
    lines.append(f"- Entity identifier: {id_var or 'not detected'}")
    lines.append(f"- Time variable: {time_var or 'not detected'}")
    lines.append("")
    lines.append("## Ranked topic directions")
    lines.append("")
    if top.empty:
        lines.append("No candidate model passed the minimal screening requirements. Check whether variables are numeric, whether sample size is sufficient, and whether key variables vary.")
    else:
        for i, row in enumerate(top.to_dict("records"), start=1):
            lines.append(f"### {i}. {topic_sentence(row, topic)}")
            lines.append("")
            lines.append(f"- Initial label: **{feasibility_label(row)}**")
            lines.append(f"- Minimal model: `{row['outcome']} ~ {row['key_variable']} + controls`")
            lines.append(f"- Usable N = {row['n']:,}; coefficient = {row['coef']:.4g}; robust SE = {row['se']:.4g}; p = {row['p']:.4g}; R2 = {row['r2']:.3f}")
            if row["p"] < 0.05:
                lines.append("- Interpretation: statistically promising as a first-pass association. Still requires identification design, theory, robustness checks and data-source validation.")
            elif row["p"] < 0.1:
                lines.append("- Interpretation: marginal initial signal. Worth exploring only if the theory is strong or an improved design is available.")
            else:
                lines.append("- Interpretation: weak initial signal under this minimal specification.")
            lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- Treat significance as a screening signal, not proof of a publishable causal effect.")
    lines.append("- Prefer topics with clear treatment timing, plausible mechanism variables, enough pre/post observations, and interpretable variable definitions.")
    lines.append("- Re-run the screen after winsorization, fixed effects, clustering, and domain-specific sample exclusions.")
    lines.append("- Do not p-hack. Use the ranked list to prioritize theory-first designs, not to report whichever model is significant.")
    (outdir / "topic_screening_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    data_path = Path(args.data).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve() if args.outdir else data_path.with_suffix("").parent / f"{data_path.stem}_topic_screen"
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_data(data_path)
    if df.empty:
        raise SystemExit("The dataset is empty.")
    infos = profile_vars(df)
    profile = pd.DataFrame([v.__dict__ for v in infos])
    profile.to_csv(outdir / "variable_profile.csv", index=False, encoding="utf-8-sig")

    y_vars, x_vars, controls, id_var, time_var = choose_candidates(infos, args)
    results: list[dict] = []
    combos = list(itertools.product(y_vars, x_vars))[: max(args.max_models * 3, args.max_models)]
    for y, x in combos:
        if y == x:
            continue
        model_controls = [c for c in controls if c not in {y, x}]
        res = fit_model(df, y, x, model_controls, time_var, args.min_n)
        if res:
            res["score"] = score_candidate(res)
            res["feasibility"] = feasibility_label(res)
            res["topic_direction"] = topic_sentence(res, args.topic)
            results.append(res)
        if len(results) >= args.max_models:
            break

    candidates = pd.DataFrame(results)
    if not candidates.empty:
        candidates = candidates.sort_values(["score", "p", "n"], ascending=[False, True, False])
    candidates.to_csv(outdir / "candidate_models.csv", index=False, encoding="utf-8-sig")
    write_report(outdir, data_path, args.topic, infos, candidates, y_vars, x_vars, controls, id_var, time_var, args)

    summary = {
        "outdir": str(outdir),
        "n_rows": int(len(df)),
        "n_columns": int(len(df.columns)),
        "n_models": int(len(candidates)),
        "top_candidates": candidates.head(args.top).to_dict("records") if not candidates.empty else [],
    }
    if args.json:
        (outdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
