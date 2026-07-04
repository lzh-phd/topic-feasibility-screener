#!/usr/bin/env python
"""Research-topic lab for CSV/DTA empirical datasets.

The script brainstorms topic directions, searches real literature metadata,
runs minimal empirical screens, validates the top topics more deeply, and
renders an HTML dashboard with charts and tables.
"""

from __future__ import annotations

import argparse
import html
import itertools
import json
import math
import random
import re
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


LITERATURE_NUMERIC_COLUMNS = [
    "literature_hits",
    "recent_2024_plus",
    "top_tier_hits",
    "peer_reviewed_hits",
    "method_hits",
    "mechanism_hits",
    "mean_paper_quality",
    "mean_relevance",
    "query_families_with_hits",
    "direct_evidence_hits",
    "bridge_evidence_hits",
    "background_evidence_hits",
    "conceptual_bridge_score",
    "innovation_gap_score",
    "theory_support_score",
    "theory_gap_score",
    "conceptual_bridge_score",
    "innovation_gap_score",
]
LITERATURE_TEXT_COLUMNS = [
    "evidence_profile",
]


ID_PAT = re.compile(r"(id|firm|company|code|stkcd|symbol|permno|cusip|证券|股票|代码|公司)", re.I)
TIME_PAT = re.compile(r"(year|yr|date|time|month|quarter|qtr|fyear|年度|年份|日期|季度)", re.I)
OUTCOME_PAT = re.compile(
    r"(score|rep|reputation|q$|tobin|roa|roe|risk|crash|turnover|return|ret|growth|"
    r"innovation|patent|constraint|sa|ww|kz|em|da|absda|analyst|forecast|fee|audit|"
    r"readability|disagreement|attention|inquiry|声誉|风险|崩盘|换手|收益|增长|创新|专利|融资|约束|盈余|分析师|审计|可读性|问询)"
)
KEY_PAT = re.compile(
    r"(treat|post|did|entry|policy|pilot|shock|dummy|high|digital|data|esg|green|"
    r"recognition|disclosure|iv|instrument|audit|internal|control|big4|入表|政策|试点|冲击|数字|数据|披露|高|绿色|审计|内控)"
)
CONTROL_PAT = re.compile(
    r"(size|lev|roa|roe|growth|bm|tobinq|board|indep|top1|soe|cash|cfo|loss|age|ato|"
    r"asset|debt|资产|负债|盈利|成长|账面|董事|独董|股权|国企|现金|亏损|年龄|周转)"
)
MECH_PAT = re.compile(
    r"(mechanism|mediator|channel|da|absda|em|readability|analyst|forecast|audit|fee|"
    r"internal|control|attention|inquiry|turnover|constraint|机制|渠道|盈余|可读性|分析师|审计|内控|关注|问询|换手|约束)"
)
POST_ONLY_PAT = re.compile(r"^(post|post_treat|after|policy_post|postpolicy|after_policy|政策后)$", re.I)


THEME_TERMS = {
    "digital transformation": ["digital", "digi", "data", "ai", "cloud", "blockchain", "internet", "数字", "数据", "人工智能", "云", "区块链"],
    "corporate reputation": ["rep", "reputation", "score", "声誉"],
    "financing constraints": ["constraint", "sa", "ww", "kz", "finance", "融资", "约束"],
    "earnings management": ["em", "da", "absda", "accrual", "盈余", "应计"],
    "capital-market response": ["turnover", "return", "ret", "volume", "q", "tobin", "换手", "收益"],
    "analyst information environment": ["analyst", "forecast", "dispersion", "分析师", "预测"],
    "audit and governance": ["audit", "fee", "big4", "internal", "control", "board", "indep", "审计", "内控", "董事"],
    "textual disclosure quality": ["readability", "readable", "mda", "mdaavg", "mdarare", "mdanum", "text", "tone", "sentiment", "annual report", "可读", "文本", "语调", "年报"],
    "innovation": ["patent", "innovation", "rd", "研发", "创新", "专利"],
    "ESG and green transition": ["esg", "green", "environment", "carbon", "绿色", "环保", "碳"],
}

TOP_JOURNAL_PAT = re.compile(
    r"^(nature|science|cell|american economic review|quarterly journal of economics|journal of political economy|"
    r"econometrica|review of economic studies|the journal of finance|journal of finance|review of financial studies|"
    r"journal of financial economics|the accounting review|accounting review|journal of accounting research|"
    r"journal of accounting and economics|management science|strategic management journal|"
    r"administrative science quarterly|academy of management journal)$",
    re.I,
)
STRONG_JOURNAL_PAT = re.compile(
    r"^(research policy|information systems research|mis quarterly|contemporary accounting research|"
    r"european accounting review|china economic review|journal of corporate finance|journal of banking & finance|"
    r"journal of banking and finance|technological forecasting and social change|business strategy and the environment|"
    r"corporate social responsibility and environmental management|journal of economic surveys|"
    r"international journal of research in marketing|journal of consumer psychology|journal of business ethics|"
    r"accounting, organizations and society|accounting organizations and society)$",
    re.I,
)
BOOK_WORK_TYPES = {"book", "book-chapter", "book-part", "monograph", "reference-book", "edited-book"}
LOW_SIGNAL_SOURCE_PAT = re.compile(r"(ssrn|research square|preprint|working paper|conference|proceedings)", re.I)
METHOD_TERMS = re.compile(r"(difference-in-differences|did|event study|instrumental variable|iv|machine learning|dml|causal|identification|panel|fixed effects)", re.I)
MECHANISM_TERMS = re.compile(r"(mechanism|channel|information asymmetry|disclosure|governance|reputation|financing|earnings management|audit|analyst)", re.I)

DATA_CONCEPT_PAT = re.compile(
    r"(data resource|data asset|data assets|enterprise data|data valuation|data assetization|"
    r"information asset|information assets|intellectual capital|knowledge asset|knowledge assets|"
    r"intangible resource|intangible resources|digital asset|digital assets|digital capital|"
    r"accounting recognition|balance[- ]sheet recognition|asset disclosure|data disclosure|"
    r"数据资源|数据资产|数据要素|数据估值|信息资产|智力资本|知识资产|无形资源|数字资产|数据披露)",
    re.I,
)
STRICT_DATA_CONCEPT_PAT = re.compile(
    r"(data resource|data asset|data assets|enterprise data|data valuation|data assetization|"
    r"accounting recognition|balance[- ]sheet recognition|data disclosure|数据资源|数据资产|数据要素|数据估值|数据披露)",
    re.I,
)
OUTCOME_CONCEPT_PAT = re.compile(
    r"(corporate reputation|reputation|stakeholder evaluation|stakeholder trust|investor judgment|"
    r"investor perception|information environment|information efficiency|information asymmetry|"
    r"market reaction|corporate image|brand reputation|trust|声誉|企业声誉|投资者判断|投资者认知|"
    r"信息环境|信息效率|信息不对称|市场反应|利益相关者|信任)",
    re.I,
)
NEGATION_OR_NULL_PAT = re.compile(
    r"(does not|do not|no evidence|insignificant|not significant|fails to|unrelated|negative effect|"
    r"no impact|doesn't|未发现|不显著|无显著|没有影响|负向|无关)",
    re.I,
)

THEORY_HINTS = {
    "digital transformation": ["digital transformation", "data assets", "data resource", "AI", "platform", "intangible assets"],
    "corporate reputation": ["corporate reputation", "stakeholder evaluation", "media reputation", "social responsibility", "trust"],
    "financing constraints": ["financing constraints", "cost of capital", "credit access", "financial flexibility"],
    "earnings management": ["earnings management", "accruals", "discretionary accruals", "financial reporting quality"],
    "capital-market response": ["stock liquidity", "turnover", "trading volume", "market reaction", "Tobin Q"],
    "analyst information environment": ["analyst following", "forecast dispersion", "forecast error", "information environment"],
    "audit and governance": ["audit quality", "audit fees", "key audit matters", "internal control", "corporate governance"],
    "textual disclosure quality": ["annual report readability", "textual disclosure", "MD&A tone", "information transparency"],
    "innovation": ["innovation", "patent", "R&D", "knowledge assets"],
    "ESG and green transition": ["ESG", "green innovation", "environmental disclosure", "carbon policy"],
}

IDEATION_LENSES = [
    ("main effect", "baseline causal or panel association"),
    ("mechanism", "why the effect happens"),
    ("economic consequence", "what the effect changes next"),
    ("heterogeneity", "where the effect is stronger or weaker"),
    ("robustness", "alternative outcome or measurement validation"),
    ("identification", "policy, IV, DDD, event-study or matching strategy"),
]


@dataclass
class VarProfile:
    name: str
    dtype: str
    n: int
    missing_rate: float
    unique: int
    mean: float | None
    std: float | None
    min: float | None
    max: float | None
    role: str
    theme: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("data", help="Input .csv or .dta dataset")
    p.add_argument("--topic", default="", help="Rough topic description; leave blank for open brainstorming")
    p.add_argument("--outdir", default=None, help="Output directory")
    p.add_argument("--y", nargs="*", default=None, help="Optional outcome candidates")
    p.add_argument("--x", nargs="*", default=None, help="Optional key/treatment candidates")
    p.add_argument("--controls", nargs="*", default=None, help="Optional controls")
    p.add_argument("--id", default=None, help="Entity id variable")
    p.add_argument("--time", default=None, help="Time variable")
    p.add_argument("--max-candidates", type=int, default=160)
    p.add_argument("--literature-top", type=int, default=30, help="How many candidates receive literature search")
    p.add_argument("--per-query", type=int, default=8)
    p.add_argument("--min-relevant-papers", type=int, default=5, help="Minimum relevant papers required before scoring literature as usable")
    p.add_argument("--min-paper-relevance", type=float, default=6.0, help="Minimum paper relevance score retained in literature summaries")
    p.add_argument("--deep-top", type=int, default=3)
    p.add_argument("--placebo-reps", type=int, default=200)
    p.add_argument("--skip-literature", action="store_true")
    p.add_argument("--scan-root", default=None, help="Optional directory to scan for additional CSV/DTA/XLSX datasets for topic expansion")
    p.add_argument("--external-max-files", type=int, default=80, help="Maximum external data files to profile when --scan-root is used")
    p.add_argument("--mailto", default="research@example.com", help="Polite OpenAlex mailto")
    p.add_argument("--seed", type=int, default=20260704)
    return p.parse_args()


def load_data(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".dta":
        return pd.read_stata(path, convert_categoricals=False)
    raise SystemExit("Unsupported file type. Use .csv or .dta.")


def load_sample(path: Path, nrows: int = 2500) -> pd.DataFrame | None:
    try:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path, nrows=nrows)
        if suffix == ".dta":
            return pd.read_stata(path, convert_categoricals=False, preserve_dtypes=False)
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(path, nrows=nrows)
    except Exception:
        return None
    return None


def scan_external_data(root: Path | None, main_path: Path, max_files: int) -> pd.DataFrame:
    if not root:
        return pd.DataFrame()
    files = []
    for ext in ("*.dta", "*.csv", "*.xlsx", "*.xls"):
        files.extend(root.rglob(ext))
    rows = []
    for path in sorted(files, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
        if len(rows) >= max_files:
            break
        if path.resolve() == main_path.resolve():
            continue
        if should_skip_external_file(path):
            continue
        df = load_sample(path)
        if df is None or df.empty:
            continue
        if looks_like_model_output(df):
            continue
        infos = profile(df)
        id_like = [v.name for v in infos if v.role == "id" or v.name.lower() in {"stkcd", "id", "firm_id"}]
        time_like = [v.name for v in infos if v.role == "time" or v.name.lower() in {"year", "fyear"}]
        outcomes = [v.name for v in infos if v.role in {"outcome", "mechanism"}][:8]
        keys = [v.name for v in infos if v.role in {"treatment", "key_x", "group"}][:8]
        controls = [v.name for v in infos if v.role == "control"][:8]
        rows.append(
            {
                "file": str(path),
                "file_name": path.name,
                "n_rows_sampled": int(len(df)),
                "n_columns": int(len(df.columns)),
                "merge_ready": bool(id_like and time_like),
                "id_candidates": "; ".join(id_like[:4]),
                "time_candidates": "; ".join(time_like[:4]),
                "outcome_candidates": "; ".join(outcomes),
                "key_candidates": "; ".join(keys),
                "control_candidates": "; ".join(controls),
                "themes": "; ".join(sorted(set(v.theme for v in infos if v.theme != "general corporate behavior"))[:8]),
            }
        )
    return pd.DataFrame(rows)


def should_skip_external_file(path: Path) -> bool:
    skip_dirs = {".git", ".statamcp", "__pycache__"}
    if any(part in skip_dirs or part.startswith("_skill_test") for part in path.parts):
        return True
    low = path.name.lower()
    return bool(
        re.search(
            r"(result|results|regression|placebo|validation|summary|report|table|"
            r"event_study|car_|ddml_|dml_|topic_scores|literature_evidence|"
            r"external_data_profile|external_topic_ideas|variable_profile)",
            low,
        )
    )


def looks_like_model_output(df: pd.DataFrame) -> bool:
    cols = {str(c).lower() for c in df.columns}
    model_cols = {"coef", "coefficient", "se", "stderr", "t", "z", "p", "pvalue", "p_value", "ci_l", "ci_u"}
    if len(cols & model_cols) >= 3:
        return True
    if len(df) <= 20 and len(cols & {"model", "variable", "outcome", "term"}) >= 1 and len(cols & model_cols) >= 2:
        return True
    return False


def external_topic_ideas(external: pd.DataFrame, topic: str) -> pd.DataFrame:
    if external.empty:
        return pd.DataFrame()
    ideas = []
    for _, r in external.iterrows():
        outcomes = [x.strip() for x in str(r.get("outcome_candidates", "")).split(";") if x.strip()]
        keys = [x.strip() for x in str(r.get("key_candidates", "")).split(";") if x.strip()]
        themes = str(r.get("themes", ""))
        for y in outcomes[:4]:
            role = external_role(y, themes)
            base = f"Use {y} from {r.get('file_name')} as a {role}"
            ideas.append(
                {
                    "idea_type": role,
                    "file_name": r.get("file_name"),
                    "candidate_variable": y,
                    "merge_ready": r.get("merge_ready"),
                    "ideation_lens": lens_for_role(role),
                    "theory_anchor": theory_anchor_for(y, themes),
                    "data_action": "left-merge by firm id and year" if r.get("merge_ready") else "inspect linkage keys before modeling",
                    "suggested_topic": f"{base} in the context of {topic or themes}",
                    "themes": themes,
                }
            )
        for x in keys[:4]:
            role = "external treatment/moderator"
            ideas.append(
                {
                    "idea_type": role,
                    "file_name": r.get("file_name"),
                    "candidate_variable": x,
                    "merge_ready": r.get("merge_ready"),
                    "ideation_lens": "heterogeneity" if re.search(r"(high|dummy|group|big4|soe|高|组|是否)", x, re.I) else "identification",
                    "theory_anchor": theory_anchor_for(x, themes),
                    "data_action": "left-merge by firm id and year" if r.get("merge_ready") else "inspect linkage keys before modeling",
                    "suggested_topic": f"Use {x} from {r.get('file_name')} as a treatment, moderator, or heterogeneity dimension for {topic or themes}",
                    "themes": themes,
                }
            )
    return pd.DataFrame(ideas)


def external_role(name: str, themes: str) -> str:
    text = f"{name} {themes}".lower()
    if re.search(r"(absda|da|em|accrual|readability|analyst|forecast|audit|internal|inquiry|盈余|可读|分析师|审计|内控|问询)", text):
        return "mechanism candidate"
    if re.search(r"(turnover|return|tobin|q|constraint|sa|fee|cost|融资|换手|收益|托宾|费用)", text):
        return "economic consequence candidate"
    if re.search(r"(score|reputation|risk|crash|innovation|patent|声誉|风险|创新|专利)", text):
        return "alternative outcome candidate"
    return "external outcome/mechanism candidate"


def lens_for_role(role: str) -> str:
    if "mechanism" in role:
        return "mechanism"
    if "consequence" in role:
        return "economic consequence"
    if "alternative outcome" in role:
        return "robustness"
    return "main effect"


def theory_anchor_for(name: str, themes: str) -> str:
    theme = theme_for(name)
    if theme == "general corporate behavior" and themes:
        theme = str(themes).split(";")[0].strip() or theme
    hints = THEORY_HINTS.get(theme, [theme])
    return "; ".join(hints[:4])


def num(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")


def theme_for(name: str) -> str:
    low = str(name).lower()
    tokens = set(t for t in re.split(r"[^a-z0-9\u4e00-\u9fff]+", low) if t)
    for theme, terms in THEME_TERMS.items():
        for term in terms:
            t = term.lower()
            if not t:
                continue
            if re.search(r"[\u4e00-\u9fff]", t):
                if t in low:
                    return theme
            elif len(t) <= 3:
                if t in tokens or low == t or low.startswith(f"{t}_") or low.endswith(f"_{t}"):
                    return theme
            elif t in low:
                return theme
    return "general corporate behavior"


def role_for(name: str, s: pd.Series, nrows: int) -> str:
    low = str(name).lower()
    numeric = num(s).notna().mean() >= 0.75
    unique = s.nunique(dropna=True)
    if ID_PAT.search(low) and unique > max(20, nrows * 0.08):
        return "id"
    if TIME_PAT.search(low):
        return "time"
    if not numeric:
        return "other"
    if KEY_PAT.search(low) and unique <= 20:
        return "treatment"
    if KEY_PAT.search(low):
        return "key_x"
    if OUTCOME_PAT.search(low):
        return "outcome"
    if CONTROL_PAT.search(low):
        return "control"
    if MECH_PAT.search(low):
        return "mechanism"
    if 2 <= unique <= 10:
        return "group"
    return "numeric"


def profile(df: pd.DataFrame) -> list[VarProfile]:
    rows: list[VarProfile] = []
    nrows = len(df)
    for c in df.columns:
        s = df[c]
        z = num(s)
        numeric = z.notna().mean() >= 0.75
        rows.append(
            VarProfile(
                name=str(c),
                dtype=str(s.dtype),
                n=int(s.notna().sum()),
                missing_rate=float(s.isna().mean()),
                unique=int(s.nunique(dropna=True)),
                mean=float(z.mean()) if numeric else None,
                std=float(z.std()) if numeric else None,
                min=float(z.min()) if numeric else None,
                max=float(z.max()) if numeric else None,
                role=role_for(str(c), s, nrows),
                theme=theme_for(str(c)),
            )
        )
    return rows


def detect_structure(infos: list[VarProfile], args: argparse.Namespace) -> dict:
    names = {v.name for v in infos}
    outcomes = args.y or [v.name for v in infos if v.role in {"outcome", "mechanism"} and v.n > 100]
    if not outcomes:
        outcomes = [v.name for v in infos if v.role == "numeric" and v.n > 100][:12]
    keys = args.x or [v.name for v in infos if v.role in {"treatment", "key_x", "group"} and v.n > 100 and not POST_ONLY_PAT.match(v.name)]
    if not keys:
        keys = [v.name for v in infos if v.role == "numeric" and v.name not in outcomes and v.n > 100][:18]
    controls = args.controls or [v.name for v in infos if v.role == "control" and v.n > 100]
    if len(controls) < 4:
        controls += [v.name for v in infos if v.role == "numeric" and v.name not in set(outcomes + keys + controls)][:10]
    id_var = args.id or next((v.name for v in infos if v.role == "id"), None)
    time_var = args.time or next((v.name for v in infos if v.role == "time"), None)
    return {
        "outcomes": [x for x in outcomes if x in names][:18],
        "keys": [x for x in keys if x in names][:22],
        "controls": [x for x in controls if x in names][:14],
        "post_candidates": [v.name for v in infos if POST_ONLY_PAT.match(v.name)][:3],
        "id": id_var if id_var in names else None,
        "time": time_var if time_var in names else None,
    }


def add_brainstorm_constructs(df: pd.DataFrame, structure: dict) -> tuple[pd.DataFrame, dict]:
    """Add safe screening-only constructs such as treatment x post.

    The raw data are not overwritten. Construct names are explicit so reports
    show that the variable is derived for screening.
    """
    out = df.copy()
    added = []
    post_vars = structure.get("post_candidates") or []
    for post in post_vars:
        if post not in out:
            continue
        candidate_keys = list(structure.get("keys", []))
        candidate_keys = sorted(
            candidate_keys,
            key=lambda k: 0 if re.search(r"(entry|drr|treat|policy|pilot|shock|data|resource|入表|政策|试点)", k.lower()) else 1,
        )
        for key in candidate_keys:
            if key not in out or key == post:
                continue
            low = key.lower()
            if not (is_binary_like(out[key]) or re.search(r"(entry|treat|pilot|policy|shock|did|入表|试点|政策)", low)):
                continue
            new = f"DID_{key}_x_{post}"
            if new in out:
                continue
            out[new] = num(out[key]).fillna(0) * num(out[post]).fillna(0)
            if out[new].nunique(dropna=True) > 1:
                added.append(new)
    if added:
        structure = dict(structure)
        structure["keys"] = added + [k for k in structure["keys"] if k not in added]
        structure["constructed_keys"] = added
    return out, structure


def clean_design(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    d = df[columns].copy()
    for c in columns:
        if c in d:
            converted = num(d[c])
            if converted.notna().mean() >= 0.75:
                d[c] = converted
    return d.replace([np.inf, -np.inf], np.nan).dropna()


def ols_hc1(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float] | None:
    n, k = X.shape
    if n <= k + 2:
        return None
    inv = np.linalg.pinv(X.T @ X)
    beta = inv @ X.T @ y
    resid = y - X @ beta
    meat = X.T @ ((resid.flatten() ** 2)[:, None] * X)
    cov = (n / max(n - k, 1)) * inv @ meat @ inv
    se = np.sqrt(np.maximum(np.diag(cov), 0)).reshape(-1, 1)
    z = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)
    p = np.vectorize(lambda x: math.erfc(abs(float(x)) / math.sqrt(2)) if np.isfinite(x) else np.nan)(z)
    ssr = float(np.sum(resid**2))
    sst = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ssr / sst if sst > 0 else np.nan
    return beta.flatten(), se.flatten(), p.flatten(), r2


def add_time_fe(d: pd.DataFrame, time_var: str | None) -> pd.DataFrame:
    if not time_var or time_var not in d or d[time_var].nunique() > 40:
        return pd.DataFrame(index=d.index)
    return pd.get_dummies(d[time_var], prefix="time", drop_first=True, dtype=float)


def minimal_model(df: pd.DataFrame, y: str, x: str, controls: list[str], time_var: str | None) -> dict | None:
    controls = [c for c in controls if c not in {y, x}]
    cols = [y, x] + controls + ([time_var] if time_var else [])
    cols = [c for c in cols if c in df.columns]
    d = clean_design(df, cols)
    if len(d) < 100 or d[y].nunique() < 5 or d[x].nunique() < 2:
        return None
    X = pd.concat([pd.Series(1.0, index=d.index, name="const"), d[[x] + controls], add_time_fe(d, time_var)], axis=1)
    fit = ols_hc1(d[y].to_numpy(float).reshape(-1, 1), X.to_numpy(float))
    if fit is None:
        return None
    beta, se, pvals, r2 = fit
    j = list(X.columns).index(x)
    return {"coef": float(beta[j]), "se": float(se[j]), "p": float(pvals[j]), "r2": float(r2), "n": int(len(d))}


def two_way_residualize(d: pd.DataFrame, var: str, id_var: str, time_var: str) -> pd.Series:
    s = d[var].astype(float)
    return s - s.groupby(d[id_var]).transform("mean") - s.groupby(d[time_var]).transform("mean") + s.mean()


def twfe_model(df: pd.DataFrame, y: str, x: str, controls: list[str], id_var: str, time_var: str) -> dict | None:
    controls = [c for c in controls if c not in {y, x}]
    cols = [y, x, id_var, time_var] + controls
    d = clean_design(df, [c for c in cols if c in df.columns])
    if len(d) < 100 or d[id_var].nunique() < 20 or d[time_var].nunique() < 2:
        return None
    ry = two_way_residualize(d, y, id_var, time_var)
    rx = pd.DataFrame({x: two_way_residualize(d, x, id_var, time_var)}, index=d.index)
    for c in controls:
        rx[c] = two_way_residualize(d, c, id_var, time_var)
    fit = ols_hc1(ry.to_numpy(float).reshape(-1, 1), rx.to_numpy(float))
    if fit is None:
        return None
    beta, se, pvals, r2 = fit
    return {"coef": float(beta[0]), "se": float(se[0]), "p": float(pvals[0]), "r2": float(r2), "n": int(len(d))}


def is_binary_like(s: pd.Series) -> bool:
    z = num(s).dropna()
    vals = set(np.round(z.unique(), 8).tolist())
    return len(vals) <= 3 and vals.issubset({0, 1, 0.0, 1.0})


def guess_design(df: pd.DataFrame, x: str, structure: dict) -> str:
    id_var, time_var = structure.get("id"), structure.get("time")
    low = x.lower()
    if id_var and time_var and is_binary_like(df[x]) and re.search(r"(entry|treat|did|post|policy|pilot|shock|入表|政策|试点)", low):
        return "DID/event study"
    if id_var and time_var:
        return "panel FE"
    return "cross-sectional/pool OLS"


def title_for(y: str, x: str, topic: str, design: str) -> str:
    lead = f"Does {x} affect {y}?"
    if design.startswith("DID"):
        lead = f"The effect of {x} on {y}: a DID design"
    if topic:
        return f"{lead} Evidence for {topic}"
    return lead


def theory_template(y: str, x: str, design: str) -> tuple[str, str]:
    xt, yt = theme_for(x), theme_for(y)
    mechanism = f"{x} may change information, governance, resource-allocation or stakeholder-evaluation channels that are reflected in {y}."
    gap = f"The likely gap is whether the {xt} literature explains {yt} outcomes under this sample, timing and identification design, rather than only documenting broad correlations."
    if design.startswith("DID"):
        gap += " A credible contribution depends on treatment timing, parallel-trend evidence and placebo tests."
    return gap, mechanism


def brainstorm(df: pd.DataFrame, infos: list[VarProfile], structure: dict, topic: str, max_candidates: int) -> pd.DataFrame:
    controls = structure["controls"]
    rows = []
    pairs = itertools.product(structure["outcomes"], structure["keys"])
    for y, x in pairs:
        if y == x:
            continue
        design = guess_design(df, x, structure)
        res = minimal_model(df, y, x, controls, structure.get("time"))
        if not res:
            continue
        gap, mechanism = theory_template(y, x, design)
        rows.append(
            {
                "topic_title": title_for(y, x, topic, design),
                "outcome": y,
                "key_variable": x,
                "design": design,
                "theory_gap": gap,
                "mechanism_logic": mechanism,
                **res,
            }
        )
        if len(rows) >= max_candidates:
            break
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["empirical_score"] = out.apply(empirical_score, axis=1)
    out["topic_alignment_score"] = out.apply(
        lambda r: topic_alignment_score(str(r["outcome"]), str(r["key_variable"]), topic),
        axis=1,
    )
    return out.sort_values(
        ["topic_alignment_score", "empirical_score", "p", "n"],
        ascending=[False, False, True, False],
    ).reset_index(drop=True)


def empirical_score(row: pd.Series) -> float:
    p = row.get("p", np.nan)
    n = row.get("n", 0)
    r2 = row.get("r2", 0)
    if not np.isfinite(p):
        return 0
    sig = pvalue_points(p)
    nscore = min(100, 20 * math.log10(max(n, 10)))
    rscore = min(100, max(0, float(r2)) * 120)
    return round(0.62 * sig + 0.25 * nscore + 0.13 * rscore, 2)


def pvalue_points(p: float | None) -> float:
    if p is None or not np.isfinite(p):
        return 0.0
    if p < 0.01:
        return 100.0
    if p < 0.05:
        return 82.0
    if p < 0.10:
        return 64.0
    if p < 0.20:
        return 42.0
    return max(5.0, 35.0 * (1.0 - min(float(p), 1.0)))


def second_pass_score(row: pd.Series) -> float:
    score = 0.0
    twfe_p = row.get("twfe_p", np.nan)
    score += 0.52 * pvalue_points(twfe_p)
    placebo_p = row.get("placebo_empirical_p", np.nan)
    if np.isfinite(placebo_p):
        score += 22.0 if placebo_p < 0.05 else 15.0 if placebo_p < 0.10 else 8.0 if placebo_p < 0.20 else 0.0
    if str(row.get("deep_design", "")).startswith("DID"):
        pre_pass = row.get("pretrend_pass", False)
        if pre_pass is True or str(pre_pass).lower() == "true":
            score += 18.0
        elif np.isfinite(row.get("pretrend_min_p", np.nan)):
            score += 6.0
    else:
        score += 8.0 if np.isfinite(twfe_p) else 0.0
    return round(min(100.0, score), 2)


def topic_alignment_score(y: str, x: str, topic: str) -> float:
    if not topic:
        return 50.0
    tokens = [t for t in re.split(r"[^A-Za-z0-9\u4e00-\u9fff]+", topic.lower()) if len(t) >= 2]
    text = f"{y} {x} {theme_for(y)} {theme_for(x)}".lower()
    hits = sum(1 for t in tokens if t in text)
    score = 40 + 12 * hits
    topic_low = topic.lower()
    x_low = x.lower()
    y_low = y.lower()
    if re.search(r"(data|resource|recognition|entry|数据|资源|入表|确认)", topic_low) and re.search(r"(entry|drr|入表|确认)", x_low):
        score += 45
        if re.fullmatch(r"(did_)?(entry|drr|treat|did)(_x_post)?", x_low):
            score += 18
        if re.search(r"(amount|amt|value|金额|数额)", x_low):
            score -= 35
    elif re.search(r"(data|resource|recognition|entry|数据|资源|入表|确认)", topic_low) and re.search(r"(data|resource|数据|资源)", x_low):
        score += 25
    if re.search(r"(reputation|声誉)", topic_low) and re.search(r"(rep|reputation|score|声誉)", y_low):
        score += 20
    if re.search(r"(data|resource|recognition|entry|数据|资源|入表|确认)", topic_low) and not re.search(r"(entry|drr|data|resource|数据|入表|确认)", x_low):
        score = min(score, 50)
    return float(max(0, min(100, score)))


def inverted_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pairs = []
    for word, positions in inv.items():
        for pos in positions:
            pairs.append((pos, word))
    return " ".join(w for _, w in sorted(pairs))[:900]


def openalex(query: str, per_page: int, mailto: str) -> list[dict]:
    params = {"search": query, "per-page": str(per_page), "mailto": mailto}
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": mailto})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.load(resp)
    rows = []
    for item in data.get("results", []):
        loc = item.get("primary_location") or {}
        source = (loc.get("source") or {}).get("display_name")
        rows.append(
            {
                "openalex_id": item.get("id"),
                "query": query,
                "title": item.get("display_name") or "",
                "year": item.get("publication_year"),
                "doi": item.get("doi"),
                "source": source,
                "work_type": item.get("type") or "",
                "authors": "; ".join(
                    [
                        (((a.get("author") or {}).get("display_name")) or "")
                        for a in (item.get("authorships") or [])[:6]
                        if (a.get("author") or {}).get("display_name")
                    ]
                ),
                "url": loc.get("landing_page_url") or item.get("doi"),
                "open_access_pdf": (item.get("open_access") or {}).get("oa_url"),
                "cited_by": item.get("cited_by_count") or 0,
                "is_oa": (item.get("open_access") or {}).get("is_oa"),
                "abstract": inverted_abstract(item.get("abstract_inverted_index")),
            }
        )
    return rows


def crossref(query: str, per_page: int, mailto: str) -> list[dict]:
    params = {"query.bibliographic": query, "rows": str(min(per_page, 20)), "mailto": mailto}
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": f"topic-feasibility-screener mailto:{mailto}"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.load(resp)
    rows = []
    for item in (data.get("message") or {}).get("items", []):
        source = "; ".join(item.get("container-title") or [])
        title = " ".join(item.get("title") or [])
        abstract = re.sub(r"<[^>]+>", " ", item.get("abstract") or "")
        year_parts = (((item.get("published-print") or item.get("published-online") or item.get("issued") or {}).get("date-parts")) or [[]])
        year = year_parts[0][0] if year_parts and year_parts[0] else None
        authors = "; ".join(
            " ".join(x for x in [a.get("given"), a.get("family")] if x)
            for a in (item.get("author") or [])[:6]
        )
        rows.append(
            {
                "provider": "crossref",
                "query": query,
                "title": title,
                "year": year,
                "doi": item.get("DOI"),
                "source": source,
                "work_type": item.get("type") or "",
                "authors": authors,
                "url": item.get("URL"),
                "open_access_pdf": "",
                "cited_by": item.get("is-referenced-by-count") or 0,
                "is_oa": "",
                "abstract": abstract[:900],
            }
        )
    return rows


def search_provider(provider: str, query: str, per_page: int, mailto: str) -> list[dict]:
    if provider == "openalex":
        return openalex(query, per_page, mailto)
    if provider == "crossref":
        return crossref(query, per_page, mailto)
    raise ValueError(f"Unknown provider: {provider}")


def literature_queries(row: pd.Series, rough_topic: str) -> list[str]:
    y, x = str(row["outcome"]), str(row["key_variable"])
    x_theme, y_theme = theme_for(x), theme_for(y)
    x_hints = THEORY_HINTS.get(x_theme, [x_theme])[:3]
    y_hints = THEORY_HINTS.get(y_theme, [y_theme])[:3]
    base = rough_topic or f"{x_theme} and {y_theme}"
    specific = compact_terms([x, y, *x_hints[:2], *y_hints[:2]])
    queries = [
        f'"{base}" empirical evidence',
        f"{specific} China listed firms empirical",
        f"{x_hints[0]} {y_hints[0]} mechanism empirical",
        f"{x_hints[0]} {y_hints[0]} difference-in-differences OR causal identification",
        f"{x_hints[0]} {y_hints[0]} 2024 2025",
        f'"intellectual capital" "{y_hints[0]}" empirical',
        f'"intangible assets" "{y_hints[0]}" disclosure empirical',
        '"information assets" investor reputation empirical',
        '"information environment" intangible assets investor judgment',
    ]
    if re.search(r"(entry|drr|data|resource|recognition|入表|数据|资源)", x.lower() + " " + base.lower()):
        queries.extend(
            [
                '"data resource" accounting recognition corporate reputation',
                '"data assets" "intangible assets" disclosure reputation',
                '"balance sheet recognition" intangible assets information asymmetry',
                '"data valuation" investor information environment',
                '"digital assets" corporate reputation investor perception',
                '"intangible assets" "corporate reputation"',
            ]
        )
    return list(dict.fromkeys(q for q in queries if q.strip()))


def compact_terms(terms: list[str]) -> str:
    seen = []
    for term in terms:
        term = str(term).strip()
        if not term:
            continue
        if len(term) > 28 and not re.search(r"\s", term):
            continue
        low = term.lower()
        if low not in seen:
            seen.append(low)
    return " ".join(seen[:6])


def dedup_records(records: Iterable[dict]) -> list[dict]:
    seen = set()
    out = []
    for r in records:
        key = (r.get("doi") or r.get("title") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def query_family(query: str) -> str:
    q = str(query).lower()
    if "search_error" in q:
        return "error"
    if "intellectual capital" in q or "intangible" in q or "information environment" in q or "data valuation" in q:
        return "bridge"
    if "2024" in q or "2025" in q or "2026" in q:
        return "recent"
    if "mechanism" in q or "channel" in q:
        return "mechanism"
    if "did" in q or "difference-in-differences" in q or "causal" in q or "identification" in q or "iv" in q:
        return "identification"
    if "empirical" in q or "listed firms" in q:
        return "empirical"
    if "accounting recognition" in q or "data assets" in q or "balance sheet" in q:
        return "construct-specific"
    return "core"


def evidence_audit(record: dict, row: pd.Series, rough_topic: str) -> dict:
    body = " ".join(str(record.get(k) or "") for k in ["title", "abstract", "source"]).lower()
    x = str(row.get("key_variable", "")).lower()
    y = str(row.get("outcome", "")).lower()
    topic = str(rough_topic or "").lower()
    strict_data_anchor = bool(STRICT_DATA_CONCEPT_PAT.search(body))
    broad_data_anchor = bool(DATA_CONCEPT_PAT.search(body))
    adjacent_asset_anchor = bool(re.search(r"(intangible assets|intangible asset|intangible resource|intangible resources|intellectual capital|information asset|information assets|无形资产|无形资源|智力资本|信息资产)", body))
    weak_data_anchor = bool(
        re.search(r"(entry|drr|data|resource|recognition|入表|数据|资源)", x + " " + topic)
        and re.search(r"(data|asset|intangible|recognition|accounting|disclosure)", body)
    )
    outcome_anchor = bool(
        OUTCOME_CONCEPT_PAT.search(body)
        or (
            re.search(r"(rep|reputation|score|声誉)", y + " " + topic)
            and re.search(r"(reputation|stakeholder|investor|trust|image|csr)", body)
        )
    )
    method_anchor = bool(METHOD_TERMS.search(body) or MECHANISM_TERMS.search(body))
    semantic_direction = "null_or_negative" if NEGATION_OR_NULL_PAT.search(body) else "supportive_or_unspecified"
    conceptual_bridge_strength = 0
    if strict_data_anchor and outcome_anchor:
        conceptual_bridge_strength = 100
    elif broad_data_anchor and outcome_anchor:
        conceptual_bridge_strength = 85
    elif (strict_data_anchor or broad_data_anchor) or outcome_anchor:
        conceptual_bridge_strength = 55
    elif adjacent_asset_anchor or weak_data_anchor or method_anchor:
        conceptual_bridge_strength = 35

    if strict_data_anchor and outcome_anchor:
        evidence = "direct"
        reason = "strict direct evidence: paper text contains explicit data-resource/data-asset/accounting-recognition language and reputation/investor/information-environment language"
    elif broad_data_anchor and outcome_anchor:
        evidence = "bridge"
        reason = "bridge evidence: paper text links a broader data/intangible/information-asset concept with reputation/investor/information-environment language"
    elif strict_data_anchor:
        evidence = "bridge"
        reason = "bridge evidence: paper text has explicit data-resource/data-asset/accounting-recognition language but lacks the outcome-side anchor"
    elif adjacent_asset_anchor and outcome_anchor:
        evidence = "bridge"
        reason = "bridge evidence: paper text connects adjacent intangible/information/intellectual-capital concepts with reputation or information-environment language"
    elif adjacent_asset_anchor:
        evidence = "bridge"
        reason = "bridge evidence: paper text has adjacent intangible/information/intellectual-capital language, useful for theory but not direct"
    elif weak_data_anchor and outcome_anchor:
        evidence = "bridge"
        reason = "bridge evidence: paper text has generic accounting/disclosure language and outcome-side language, but lacks explicit data-resource/data-asset recognition language"
    elif weak_data_anchor:
        evidence = "background"
        reason = "paper text has generic accounting/disclosure language only; topic/query words are not allowed to create direct evidence"
    elif outcome_anchor:
        evidence = "background"
        reason = "paper text has reputation/investor/information-environment language but lacks explicit data-resource/data-asset recognition language"
    elif method_anchor:
        evidence = "background"
        reason = "paper text has method or mechanism language but lacks the required two-sided content anchors"
    else:
        evidence = "weak"
        reason = "paper text lacks both required direct-evidence anchors"
    return {
        "text_data_anchor": int(strict_data_anchor),
        "broad_data_concept_anchor": int(broad_data_anchor),
        "adjacent_asset_anchor": int(adjacent_asset_anchor),
        "generic_data_or_disclosure_anchor": int(weak_data_anchor),
        "text_outcome_anchor": int(outcome_anchor),
        "method_or_mechanism_anchor": int(method_anchor),
        "direct_requirements_met": int(strict_data_anchor and outcome_anchor),
        "conceptual_bridge_strength_pct": conceptual_bridge_strength,
        "semantic_direction": semantic_direction,
        "evidence_class": evidence,
        "evidence_reason": reason,
    }


def evidence_class(record: dict, row: pd.Series, rough_topic: str) -> str:
    audit = evidence_audit(record, row, rough_topic)
    return str(audit["evidence_class"])


def corrected_source_type(record: dict) -> str:
    source = str(record.get("source") or "").strip()
    work_type = str(record.get("work_type") or "").strip().lower()
    doi = str(record.get("doi") or "").lower()
    src_low = source.lower()
    if doi.startswith("10.2139/") or "ssrn" in src_low:
        return "working/preprint"
    if work_type in BOOK_WORK_TYPES or re.search(r"(handbook|book|chapter|edited volume|monograph)", src_low):
        return "book/chapter"
    if work_type == "journal-article" or source:
        return "journal article"
    return "unknown"


def no_literature_summary(candidate_index: int | None, status: str) -> dict:
    out = {c: np.nan for c in LITERATURE_NUMERIC_COLUMNS}
    out.update({c: "" for c in LITERATURE_TEXT_COLUMNS})
    out.update(
        {
            "candidate_index": candidate_index,
            "literature_status": status,
            "literature_search_state": status,
            "queries_run": 0,
            "raw_literature_hits": 0,
            "relevant_literature_hits": 0,
            "search_errors": 0,
            "query_diagnostics": "",
        }
    )
    return out


def journal_tier_score(record: dict) -> tuple[float, str]:
    source = str(record.get("source") or "").strip()
    src_type = corrected_source_type(record)
    if src_type == "working/preprint":
        return 5.5, "frontier working/preprint"
    if src_type == "book/chapter":
        return 5.5, "book/chapter"
    if LOW_SIGNAL_SOURCE_PAT.search(source):
        return 5.5, "frontier working/preprint"
    if TOP_JOURNAL_PAT.search(source):
        return 22.0, "top"
    if STRONG_JOURNAL_PAT.search(source):
        return 16.5, "strong peer-reviewed"
    if src_type == "journal article":
        return 11.0, "peer-reviewed/manual-tier-check"
    if source:
        return 5.5, "indexed/manual-check"
    return 1.0, "unknown"


def relevance_score(record: dict, row: pd.Series, rough_topic: str) -> float:
    text = " ".join(
        str(record.get(k) or "")
        for k in ["title", "abstract", "source"]
    ).lower()
    y = str(row["outcome"]).lower()
    x = str(row["key_variable"]).lower()
    theme_y = theme_for(y).lower()
    theme_x = theme_for(x).lower()
    score = 0.0
    for term in [y, x, theme_y, theme_x]:
        tokens = [t for t in re.split(r"[^a-z0-9\u4e00-\u9fff]+", term) if len(t) >= 3]
        score += min(10, 2.5 * sum(1 for t in tokens if t in text))
    for t in re.split(r"[^a-z0-9\u4e00-\u9fff]+", rough_topic.lower()):
        if len(t) >= 4 and t in text:
            score += 1.5
    if re.search(r"(data resource|data assets|accounting recognition|balance sheet recognition)", text) and re.search(r"(entry|drr|data|resource|recognition|入表|数据)", x):
        score += 6.0
    if "reputation" in text and re.search(r"(rep|reputation|score|声誉)", y):
        score += 4.0
    return min(25.0, score)


def paper_quality(record: dict, row: pd.Series, rough_topic: str) -> dict:
    tier_score, tier = journal_tier_score(record)
    src_type = corrected_source_type(record)
    year = record.get("year")
    try:
        year_i = int(year)
    except Exception:
        year_i = 0
    recency = 0.0
    if year_i >= 2025:
        recency = 8.0
    elif year_i >= 2023:
        recency = 6.0
    elif year_i >= 2019:
        recency = 3.5
    elif year_i:
        recency = 1.0
    cited = float(record.get("cited_by") or 0)
    citation_score = min(10.0, math.log1p(cited) * 2.0)
    text = f"{record.get('title') or ''} {record.get('abstract') or ''}"
    method_score = 5.0 if METHOD_TERMS.search(text) else 0.0
    mechanism_score = 5.0 if MECHANISM_TERMS.search(text) else 0.0
    rel = relevance_score(record, row, rough_topic)
    quality = tier_score + recency + citation_score + method_score + mechanism_score + rel
    if src_type in {"working/preprint", "book/chapter"}:
        quality = min(quality, 32.0)
    quality_score = round(min(70.0, quality), 2)
    rel_score = round(rel, 2)
    return {
        "paper_quality_score": quality_score,
        "paper_quality_pct": round(quality_score / 70.0 * 100.0, 2),
        "journal_tier": tier,
        "source_type": src_type,
        "journal_tier_score": tier_score,
        "journal_tier_pct": round(min(tier_score / 22.0 * 100.0, 100.0), 2),
        "paper_relevance_score": rel_score,
        "paper_relevance_pct": round(rel_score / 25.0 * 100.0, 2),
        "paper_recency_score": recency,
        "paper_recency_pct": round(recency / 8.0 * 100.0, 2) if recency else 0.0,
        "paper_citation_score": round(citation_score, 2),
        "paper_citation_pct": round(citation_score / 10.0 * 100.0, 2),
        "paper_method_score": method_score,
        "paper_method_pct": round(method_score / 5.0 * 100.0, 2) if method_score else 0.0,
        "paper_mechanism_score": mechanism_score,
        "paper_mechanism_pct": round(mechanism_score / 5.0 * 100.0, 2) if mechanism_score else 0.0,
    }


def theory_scores(records: list[dict]) -> dict:
    valid = [r for r in records if r.get("year")]
    if not valid:
        return no_literature_summary(None, "searched but no relevant records")
    qualities = np.array([float(r.get("paper_quality_score") or 0) for r in valid])
    relevances = np.array([float(r.get("paper_relevance_score") or 0) for r in valid])
    direction_penalty = sum(1 for r in valid if r.get("semantic_direction") == "null_or_negative")
    top_sum = float(np.sum(np.sort(qualities)[-12:]))
    density_bonus = min(14.0, len(valid) * 0.65)
    recent = sum(1 for r in valid if int(r.get("year") or 0) >= 2024)
    recent_bonus = min(12.0, recent * 1.8)
    top_hits = sum(1 for r in valid if r.get("journal_tier") == "top")
    peer_hits = sum(1 for r in valid if r.get("journal_tier") in {"top", "strong peer-reviewed", "peer-reviewed/manual-tier-check"})
    method_hits = sum(1 for r in valid if float(r.get("paper_method_score") or 0) > 0)
    mechanism_hits = sum(1 for r in valid if float(r.get("paper_mechanism_score") or 0) > 0)
    direct_hits = sum(1 for r in valid if r.get("evidence_class") == "direct")
    bridge_hits = sum(1 for r in valid if r.get("evidence_class") == "bridge")
    background_hits = sum(1 for r in valid if r.get("evidence_class") == "background")
    bridge_strengths = np.array([float(r.get("conceptual_bridge_strength_pct") or 0) for r in valid])
    conceptual_bridge_score = float(np.nanmean(bridge_strengths)) if len(bridge_strengths) else 0.0
    query_hits = len({str(r.get("query_family") or query_family(str(r.get("query") or ""))) for r in valid if r.get("query")})
    relevance_bonus = min(15.0, float(np.nanmean(relevances)) * 0.55 if len(relevances) else 0)
    support = min(
        100.0,
        top_sum / 7.5
        + density_bonus
        + recent_bonus
        + relevance_bonus
        + min(10, top_hits * 2.2)
        + min(9, method_hits * 1.1)
        + min(9, mechanism_hits * 1.1)
        + min(6, query_hits * 1.0),
    )
    if direct_hits == 0:
        bridge_bonus = min(30.0, bridge_hits * 1.7 + conceptual_bridge_score * 0.15)
        bridge_cap = 88.0 if bridge_hits >= 8 else 78.0
        support = min(bridge_cap, support * 0.82 + bridge_bonus)
    elif direct_hits < 2:
        support = min(support, 72.0)
    elif direct_hits < 5:
        support = min(support, 82.0 + 2 * direct_hits)
    support = max(15.0, support - min(10.0, direction_penalty * 2.0))

    density = len(valid)
    crowding_penalty = max(0.0, density - 35) * 0.7 + max(0.0, top_hits - 7) * 1.4
    thin_penalty = max(0.0, 10 - density) * 4.4
    evidence_balance = min(10.0, query_hits * 0.9 + recent * 0.8 + method_hits * 0.45 + mechanism_hits * 0.45)
    narrowness_penalty = 10.0 if np.nanmean(relevances) < 6 else 0.0
    if direct_hits == 0 and bridge_hits >= 8:
        innovation_gap = min(95.0, 52.0 + min(24.0, bridge_hits * 1.2) + min(12.0, recent * 1.2) + min(7.0, query_hits * 1.0))
    elif direct_hits == 0 and bridge_hits >= 3:
        innovation_gap = min(78.0, 42.0 + bridge_hits * 2.0 + min(8.0, recent * 1.0))
    elif direct_hits == 0 and background_hits >= 6:
        innovation_gap = min(68.0, 45.0 + background_hits * 1.2 + min(8.0, recent * 1.0) + min(5.0, query_hits * 0.8))
    else:
        innovation_gap = max(15.0, 50.0 - direct_hits * 2.0)
    direct_penalty = 0.0 if bridge_hits >= 8 else max(0.0, 3 - direct_hits) * (3.0 if background_hits >= 6 else 5.0)
    gap = 76.0 + evidence_balance - crowding_penalty - thin_penalty - narrowness_penalty
    gap -= direct_penalty
    if direct_hits == 0 and bridge_hits >= 8:
        gap = max(gap, innovation_gap)
    elif direct_hits == 0 and bridge_hits == 0 and background_hits >= 6:
        gap = max(gap, innovation_gap)
    gap = max(15.0, gap - min(8.0, direction_penalty * 1.5))
    gap = float(max(15.0, min(95.0, gap)))
    if direct_hits > 0:
        evidence_profile = "direct evidence found"
    elif bridge_hits > 0:
        evidence_profile = "direct evidence gap with bridge literature support"
    elif background_hits >= 6:
        evidence_profile = "direct and bridge evidence gap, but active one-sided background literature suggests a possible frontier gap"
    elif background_hits > 0:
        evidence_profile = "thin one-sided background literature; theory needs manual strengthening"
    else:
        evidence_profile = "no usable theory footing found in searched metadata"
    return {
        "literature_hits": density,
        "recent_2024_plus": recent,
        "top_tier_hits": top_hits,
        "peer_reviewed_hits": peer_hits,
        "method_hits": method_hits,
        "mechanism_hits": mechanism_hits,
        "mean_paper_quality": round(float(np.nanmean(qualities)), 2),
        "mean_relevance": round(float(np.nanmean(relevances)), 2),
        "query_families_with_hits": query_hits,
        "direct_evidence_hits": direct_hits,
        "bridge_evidence_hits": bridge_hits,
        "background_evidence_hits": background_hits,
        "conceptual_bridge_score": round(conceptual_bridge_score, 2),
        "innovation_gap_score": round(innovation_gap, 2),
        "theory_support_score": round(support, 2),
        "theory_gap_score": round(gap, 2),
        "evidence_profile": evidence_profile,
        "literature_status": literature_status(density, recent, top_hits, method_hits, mechanism_hits),
        "literature_search_state": "searched",
    }


def search_literature(candidates: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    all_records = []
    summaries = []
    diagnostics = []
    if args.skip_literature or candidates.empty:
        if candidates.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        summaries = [
            no_literature_summary(int(idx), "not searched (--skip-literature)")
            for idx, _ in candidates.iterrows()
        ]
        return pd.DataFrame(summaries), pd.DataFrame(), pd.DataFrame()
    for idx, row in candidates.head(args.literature_top).iterrows():
        records = []
        for q in literature_queries(row, args.topic):
            for provider in ["openalex", "crossref"]:
                diag = {
                    "candidate_index": idx,
                    "candidate_title": row["topic_title"],
                    "provider": provider,
                    "query": q,
                    "query_family": query_family(q),
                    "raw_hits": 0,
                    "valid_hits": 0,
                    "relevant_hits": 0,
                    "status": "ok",
                    "error": "",
                }
                try:
                    got = search_provider(provider, q, args.per_query, args.mailto)
                    for g in got:
                        g.setdefault("provider", provider)
                    records.extend(got)
                    diag["raw_hits"] = len(got)
                    diag["valid_hits"] = sum(1 for r in got if r.get("year"))
                except HTTPError as exc:
                    diag["status"] = "rate_limited" if exc.code == 429 else "error"
                    diag["error"] = f"HTTP {exc.code}: {exc.reason}"
                    records.append({"provider": provider, "query": q, "title": f"SEARCH_ERROR: {exc}", "year": None, "search_error": str(exc)})
                except Exception as exc:
                    diag["status"] = "error"
                    diag["error"] = str(exc)
                    records.append({"provider": provider, "query": q, "title": f"SEARCH_ERROR: {exc}", "year": None, "search_error": str(exc)})
                time.sleep(0.35 if provider == "openalex" else 0.2)
                diagnostics.append(diag)
        raw_count = len([r for r in records if r.get("year")])
        records = dedup_records(records)
        valid_all = [r for r in records if r.get("year")]
        for r in valid_all:
            r.update(paper_quality(r, row, args.topic))
            r["query_family"] = query_family(str(r.get("query") or ""))
            r.update(evidence_audit(r, row, args.topic))
        scoring_records = [
            r for r in valid_all
            if float(r.get("paper_relevance_score") or 0) >= args.min_paper_relevance
            and r.get("evidence_class") in {"direct", "bridge", "background"}
        ]
        evidence_priority = {"direct": 3, "bridge": 2, "background": 1}
        scoring_records = sorted(
            scoring_records,
            key=lambda r: (
                evidence_priority.get(str(r.get("evidence_class")), 0),
                float(r.get("paper_quality_score") or 0),
                float(r.get("paper_relevance_score") or 0),
            ),
            reverse=True,
        )[:18]
        display_records = sorted(valid_all, key=lambda r: float(r.get("paper_quality_score") or 0), reverse=True)[:12]
        summary = theory_scores(scoring_records)
        summary["candidate_index"] = idx
        summary["queries_run"] = len(literature_queries(row, args.topic))
        summary["raw_literature_hits"] = raw_count
        summary["relevant_literature_hits"] = len(scoring_records)
        summary["search_errors"] = sum(1 for r in records if r.get("search_error"))
        summary["query_diagnostics"] = "; ".join(
            f"{d['query_family']}:{d['valid_hits']}/{d['raw_hits']}{' ERR' if d['status']=='error' else ''}"
            for d in diagnostics
            if d["candidate_index"] == idx
        )
        cand_diags = [d for d in diagnostics if d["candidate_index"] == idx]
        all_rate_limited = bool(cand_diags) and all(d["status"] == "rate_limited" for d in cand_diags)
        any_rate_limited = any(d["status"] == "rate_limited" for d in cand_diags)
        if len(scoring_records) < args.min_relevant_papers:
            summary["literature_search_state"] = "rate_limited" if all_rate_limited else "searched_insufficient_relevance"
            if all_rate_limited:
                summary["literature_status"] = "literature search rate-limited; scores unavailable, rerun later or increase mailto/polite-pool"
            elif any_rate_limited:
                summary["literature_status"] = f"partially rate-limited; only {len(scoring_records)} relevant papers passed the relevance screen"
            else:
                summary["literature_status"] = f"searched but only {len(scoring_records)} relevant papers passed the relevance screen"
            for c in ["theory_support_score", "theory_gap_score"]:
                summary[c] = np.nan
        summaries.append(summary)
        for d in diagnostics:
            if d["candidate_index"] == idx:
                d["relevant_hits"] = sum(1 for r in scoring_records if r.get("query") == d["query"])
        for r in display_records:
            r["candidate_index"] = idx
            r["candidate_title"] = row["topic_title"]
            r["passes_relevance_screen"] = float(r.get("paper_relevance_score") or 0) >= args.min_paper_relevance
            all_records.append(r)
    for idx, _ in candidates.iloc[args.literature_top :].iterrows():
        summaries.append(no_literature_summary(int(idx), "not searched (outside --literature-top limit)"))
    return pd.DataFrame(summaries), pd.DataFrame(all_records), pd.DataFrame(diagnostics)


def literature_status(hits: int, recent: int, top_hits: int = 0, method_hits: int = 0, mechanism_hits: int = 0) -> str:
    if hits >= 35 and top_hits >= 5:
        return "dense: sharpen mechanism or identification to avoid incremental framing"
    if hits >= 12 and recent >= 3 and (method_hits or mechanism_hits):
        return "active and usable: recent work and mechanism/identification anchors exist"
    if hits >= 8:
        return "thin-to-moderate: possible novelty but framing burden is higher"
    return "too thin or search failed: needs broader search before trusting the theory"


def merge_scores(candidates: pd.DataFrame, lit_summary: pd.DataFrame) -> pd.DataFrame:
    out = candidates.copy()
    if not lit_summary.empty:
        out = out.merge(lit_summary, left_index=True, right_on="candidate_index", how="left").set_index("candidate_index", drop=False)
        out = out.sort_index()
    for c in LITERATURE_NUMERIC_COLUMNS:
        if c not in out:
            out[c] = np.nan
        out[c] = pd.to_numeric(out[c], errors="coerce")
    for c in LITERATURE_TEXT_COLUMNS:
        if c not in out:
            out[c] = ""
        out[c] = out[c].fillna("")
    for c in ["literature_status", "literature_search_state", "query_diagnostics"]:
        if c not in out:
            out[c] = "not searched"
        out[c] = out[c].fillna("not searched")
    for c in ["queries_run", "raw_literature_hits", "relevant_literature_hits", "search_errors"]:
        if c not in out:
            out[c] = np.nan
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if "topic_alignment_score" not in out:
        out["topic_alignment_score"] = 50
    out["topic_alignment_score"] = out["topic_alignment_score"].fillna(50)
    out["empirical_score_final"] = out.get("empirical_score_final", out["empirical_score"])
    out["first_pass_empirical_score"] = out.get("first_pass_empirical_score", out["empirical_score"])
    out["second_pass_score"] = out.get("second_pass_score", np.nan)
    design_bonus = out["design"].map({"DID/event study": 8, "panel FE": 5, "cross-sectional/pool OLS": 0}).fillna(0)
    theory_support_for_rank = out["theory_support_score"].fillna(35)
    theory_gap_for_rank = out["theory_gap_score"].fillna(35)
    out["overall_score"] = (
        0.32 * out["empirical_score_final"]
        + 0.28 * theory_support_for_rank
        + 0.15 * theory_gap_for_rank
        + 0.25 * out["topic_alignment_score"]
        + design_bonus
    ).clip(0, 100).round(2)
    out["priority_rank"] = out["key_variable"].apply(primary_topic_priority)
    out["feasibility_label"] = out["overall_score"].apply(lambda x: "A-level" if x >= 82 else "B-level" if x >= 68 else "C-level" if x >= 52 else "reject/backup")
    return out.sort_values(["priority_rank", "overall_score", "empirical_score_final"], ascending=[False, False, False]).reset_index(drop=True)


def primary_topic_priority(key: str) -> int:
    low = str(key).lower()
    if re.fullmatch(r"(did_)?(entry|drr|treat|did)(_x_post)?", low):
        return 3
    if re.search(r"(entry|drr|入表|确认)", low) and not re.search(r"(amount|amt|value|金额|数额)", low):
        return 3
    if re.search(r"(entry|drr|data|resource|数据|入表|确认)", low):
        return 2
    return 1


def did_event_study(df: pd.DataFrame, y: str, x: str, controls: list[str], id_var: str, time_var: str) -> dict:
    d = clean_design(df, [y, x, id_var, time_var] + controls)
    d[x] = (d[x] > 0).astype(int)
    first = d[d[x] == 1].groupby(id_var)[time_var].min()
    d["_first_treat"] = d[id_var].map(first)
    d["_ever"] = d["_first_treat"].notna().astype(int)
    if d["_ever"].sum() == 0:
        return {"deep_design": "DID/event study", "deep_status": "no treated units detected"}
    d["_event"] = d[time_var] - d["_first_treat"]
    windows = [-3, -2, 0, 1, 2]
    event_cols = []
    for w in windows:
        c = f"event_{w}"
        d[c] = ((d["_event"] == w) & (d["_ever"] == 1)).astype(float)
        if d[c].sum() > 0:
            event_cols.append(c)
    reg_controls = [c for c in controls if c in d.columns and c not in {y, x}]
    base = twfe_model(d, y, x, reg_controls, id_var, time_var)
    event_results = {}
    if event_cols:
        ry = two_way_residualize(d, y, id_var, time_var)
        X = pd.DataFrame(index=d.index)
        for c in event_cols + reg_controls:
            X[c] = two_way_residualize(d, c, id_var, time_var)
        fit = ols_hc1(ry.to_numpy(float).reshape(-1, 1), X.to_numpy(float))
        if fit:
            beta, se, pvals, _ = fit
            for i, c in enumerate(X.columns[: len(event_cols)]):
                event_results[c] = {"coef": float(beta[i]), "se": float(se[i]), "p": float(pvals[i])}
    pre_ps = [v["p"] for k, v in event_results.items() if k in {"event_-3", "event_-2"} and np.isfinite(v["p"])]
    return {
        "deep_design": "DID/event study",
        "twfe_coef": base.get("coef") if base else np.nan,
        "twfe_p": base.get("p") if base else np.nan,
        "pretrend_pass": bool(pre_ps and all(p > 0.10 for p in pre_ps)),
        "pretrend_min_p": min(pre_ps) if pre_ps else np.nan,
        "event_results": event_results,
        "deep_status": "event-study pretrend check and TWFE validation completed",
    }


def placebo(df: pd.DataFrame, y: str, x: str, controls: list[str], id_var: str | None, time_var: str | None, reps: int, seed: int) -> dict:
    rng = random.Random(seed)
    base = twfe_model(df, y, x, controls, id_var, time_var) if id_var and time_var else minimal_model(df, y, x, controls, time_var)
    if not base or not np.isfinite(base["coef"]):
        return {"placebo_status": "base model unavailable"}
    d = df.copy()
    vals = num(d[x])
    coefs = []
    for _ in range(reps):
        shuffled = vals.sample(frac=1, random_state=rng.randint(1, 10_000_000)).to_numpy()
        d["_placebo_x"] = shuffled
        res = twfe_model(d, y, "_placebo_x", controls, id_var, time_var) if id_var and time_var else minimal_model(d, y, "_placebo_x", controls, time_var)
        if res and np.isfinite(res["coef"]):
            coefs.append(res["coef"])
    if not coefs:
        return {"placebo_status": "placebo failed"}
    p_emp = float(np.mean(np.abs(coefs) >= abs(base["coef"])))
    return {"placebo_empirical_p": p_emp, "placebo_reps": len(coefs), "placebo_status": "completed"}


def deep_validate(df: pd.DataFrame, ranked: pd.DataFrame, structure: dict, args: argparse.Namespace) -> pd.DataFrame:
    rows = []
    controls = structure["controls"]
    for _, row in ranked.head(args.deep_top).iterrows():
        y, x = row["outcome"], row["key_variable"]
        record = {"topic_title": row["topic_title"], "outcome": y, "key_variable": x, "design": row["design"]}
        if row["design"].startswith("DID") and structure.get("id") and structure.get("time"):
            record.update(did_event_study(df, y, x, controls, structure["id"], structure["time"]))
        elif structure.get("id") and structure.get("time"):
            fe = twfe_model(df, y, x, controls, structure["id"], structure["time"])
            record.update({"deep_design": "panel FE", "twfe_coef": fe.get("coef") if fe else np.nan, "twfe_p": fe.get("p") if fe else np.nan, "deep_status": "two-way FE robustness completed"})
        else:
            alt = minimal_model(df, y, x, controls, structure.get("time"))
            record.update({"deep_design": "pooled robustness", "twfe_coef": alt.get("coef") if alt else np.nan, "twfe_p": alt.get("p") if alt else np.nan, "deep_status": "pooled robustness completed"})
        record.update(placebo(df, y, x, controls, structure.get("id"), structure.get("time"), args.placebo_reps, args.seed + len(rows)))
        record["second_pass_score"] = second_pass_score(pd.Series(record))
        rows.append(record)
    return pd.DataFrame(rows)


def apply_second_pass_scores(ranked: pd.DataFrame, deep: pd.DataFrame) -> pd.DataFrame:
    out = ranked.copy()
    out["first_pass_empirical_score"] = out["empirical_score"]
    out["second_pass_score"] = np.nan
    if not deep.empty:
        for _, d in deep.iterrows():
            mask = (out["outcome"] == d.get("outcome")) & (out["key_variable"] == d.get("key_variable"))
            out.loc[mask, "second_pass_score"] = d.get("second_pass_score")
    out["empirical_score_final"] = out.apply(
        lambda r: round(0.55 * r["first_pass_empirical_score"] + 0.45 * r["second_pass_score"], 2)
        if np.isfinite(r.get("second_pass_score", np.nan))
        else r["first_pass_empirical_score"],
        axis=1,
    )
    return out


def validation_checks(
    outdir: Path,
    df: pd.DataFrame,
    ranked: pd.DataFrame,
    profiles: pd.DataFrame,
    lit: pd.DataFrame,
    deep: pd.DataFrame,
    external: pd.DataFrame,
    query_diag: pd.DataFrame,
    args: argparse.Namespace,
) -> pd.DataFrame:
    chart_dir = outdir / "charts"
    chart_files = sorted(chart_dir.glob("*.html")) if chart_dir.exists() else []
    states = ranked.get("literature_search_state", pd.Series(dtype=str)).fillna("not searched")
    direct_hits = pd.to_numeric(ranked.get("direct_evidence_hits", pd.Series(dtype=float)), errors="coerce").fillna(0)
    bridge_hits = pd.to_numeric(ranked.get("bridge_evidence_hits", pd.Series(dtype=float)), errors="coerce").fillna(0)
    innovation_gap = pd.to_numeric(ranked.get("innovation_gap_score", pd.Series(dtype=float)), errors="coerce")
    rows = [
        {
            "function": "data_reading",
            "passed": bool(len(df) > 0 and len(df.columns) > 1 and not profiles.empty),
            "detail": f"rows={len(df)}, columns={len(df.columns)}, profiled_variables={len(profiles)}",
        },
        {
            "function": "topic_brainstorming",
            "passed": bool(len(ranked) >= min(8, args.max_candidates) and ranked["outcome"].nunique() >= 2 and ranked["key_variable"].nunique() >= 2),
            "detail": f"topics={len(ranked)}, outcomes={ranked['outcome'].nunique()}, key_variables={ranked['key_variable'].nunique()}",
        },
        {
            "function": "external_data_expansion",
            "passed": bool(len(external) > 0),
            "detail": f"external_files_profiled={len(external)}",
        },
        {
            "function": "literature_search_diagnostics",
            "passed": bool(args.skip_literature or (not query_diag.empty and states.isin(['searched', 'searched_insufficient_relevance', 'rate_limited']).any())),
            "detail": "skipped" if args.skip_literature else f"queries={len(query_diag)}, states={states.value_counts().to_dict()}",
        },
        {
            "function": "literature_strict_scoring",
            "passed": bool(args.skip_literature or lit.empty or ("source_type" in lit.columns and "evidence_class" in lit.columns)),
            "detail": "source_type and evidence_class present; direct, bridge, background and weak evidence are separated",
        },
        {
            "function": "second_pass_validation",
            "passed": bool(len(deep) >= min(args.deep_top, len(ranked))),
            "detail": f"deep_rows={len(deep)}, requested={min(args.deep_top, len(ranked))}",
        },
        {
            "function": "visual_dashboard_links",
            "passed": bool(len(chart_files) >= 4),
            "detail": f"chart_files={len(chart_files)}",
        },
        {
            "function": "direct_zero_gap_logic",
            "passed": bool(args.skip_literature or ranked["theory_support_score"].isna().any() or innovation_gap.notna().any() or bridge_hits.sum() == 0),
            "detail": "zero direct evidence is handled through bridge evidence and innovation_gap_score rather than a hard support cap",
        },
    ]
    checks = pd.DataFrame(rows)
    checks.to_csv(outdir / "feature_validation_checks.csv", index=False, encoding="utf-8-sig")
    return checks


def fmt(x, digits: int = 3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    try:
        if pd.isna(x):
            return "NA"
    except Exception:
        pass
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    if isinstance(x, (float, np.floating)):
        ax = abs(float(x))
        if ax >= 1_000_000_000:
            return f"{x/1_000_000_000:.2f}B"
        if ax >= 1_000_000:
            return f"{x/1_000_000:.2f}M"
        if ax >= 10_000:
            return f"{x/1_000:.1f}K"
        return f"{x:.{digits}f}"
    return html.escape(str(x))


def finite_score(x, default: float | None = None) -> float | None:
    try:
        v = float(x)
        if np.isfinite(v):
            return max(0.0, min(100.0, v))
    except Exception:
        pass
    return default


def score_bar(rows: pd.DataFrame, value: str, label: str, color: str) -> str:
    rows = rows.head(10)
    width, row_h = 820, 28
    height = 40 + row_h * len(rows)
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="{html.escape(label)}">']
    parts.append(f'<text x="8" y="22" class="chart-title">{html.escape(label)}</text>')
    for i, (_, r) in enumerate(rows.iterrows()):
        y = 40 + i * row_h
        val = finite_score(r.get(value))
        parts.append(f'<text x="8" y="{y+17}" class="axis">{i+1}. {html.escape(str(r["outcome"]))} / {html.escape(str(r["key_variable"]))}</text>')
        parts.append(f'<rect x="290" y="{y+4}" width="500" height="16" fill="#edf2f7" rx="3"/>')
        if val is None:
            parts.append(f'<text x="798" y="{y+17}" text-anchor="end" class="axis">NA</text>')
        else:
            parts.append(f'<rect x="290" y="{y+4}" width="{5*val:.1f}" height="16" fill="{color}" rx="3"/>')
            parts.append(f'<text x="798" y="{y+17}" text-anchor="end" class="axis">{val:.1f}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def grouped_score_bars(rows: pd.DataFrame, values: list[tuple[str, str, str]], label: str) -> str:
    rows = rows.head(8)
    width, row_h = 880, 40
    height = 44 + row_h * len(rows)
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="{html.escape(label)}">']
    parts.append(f'<text x="8" y="22" class="chart-title">{html.escape(label)}</text>')
    for i, (_, r) in enumerate(rows.iterrows()):
        y = 42 + i * row_h
        parts.append(f'<text x="8" y="{y+12}" class="axis">{i+1}. {html.escape(str(r["outcome"]))} / {html.escape(str(r["key_variable"]))}</text>')
        for j, (col, short, color) in enumerate(values):
            val = finite_score(r.get(col))
            yy = y + 17 + j * 7
            parts.append(f'<rect x="305" y="{yy}" width="500" height="5" fill="#edf2f7" rx="2"/>')
            if val is not None:
                parts.append(f'<rect x="305" y="{yy}" width="{5*val:.1f}" height="5" fill="{color}" rx="2"><title>{html.escape(short)}: {val:.1f}</title></rect>')
        parts.append(f'<text x="816" y="{y+22}" class="axis">{fmt(r.get(values[0][0], 0),1)} / {fmt(r.get(values[1][0], 0),1)}</text>')
    lx = 8
    for col, short, color in values:
        parts.append(f'<rect x="{lx}" y="{height-16}" width="10" height="10" fill="{color}" rx="2"/>')
        parts.append(f'<text x="{lx+14}" y="{height-7}" class="axis">{html.escape(short)}</text>')
        lx += 130
    parts.append("</svg>")
    return "\n".join(parts)


def theme_distribution_chart(external: pd.DataFrame) -> str:
    if external.empty or "themes" not in external:
        return "<p>No external themes detected.</p>"
    counts: dict[str, int] = {}
    for themes in external["themes"].fillna(""):
        for theme in [t.strip() for t in str(themes).split(";") if t.strip()]:
            counts[theme] = counts.get(theme, 0) + 1
    if not counts:
        return "<p>No external themes detected.</p>"
    rows = pd.DataFrame([{"theme": k, "count": v} for k, v in counts.items()]).sort_values("count", ascending=False).head(12)
    width, row_h = 760, 28
    height = 42 + row_h * len(rows)
    max_count = max(rows["count"])
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="External data themes">']
    parts.append('<text x="8" y="22" class="chart-title">External data theme coverage</text>')
    for i, (_, r) in enumerate(rows.iterrows()):
        y = 42 + i * row_h
        val = int(r["count"])
        parts.append(f'<text x="8" y="{y+16}" class="axis">{html.escape(str(r["theme"]))}</text>')
        parts.append(f'<rect x="250" y="{y+4}" width="430" height="16" fill="#edf2f7" rx="3"/>')
        parts.append(f'<rect x="250" y="{y+4}" width="{430*val/max_count:.1f}" height="16" fill="#0f766e" rx="3"/>')
        parts.append(f'<text x="700" y="{y+16}" class="axis">{val}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def scatter(rows: pd.DataFrame) -> str:
    rows = rows.head(30)
    w, h, pad = 520, 360, 48
    parts = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="Theory versus empirical feasibility">']
    parts.append('<text x="8" y="22" class="chart-title">Theory vs empirical feasibility</text>')
    parts.append(f'<line x1="{pad}" y1="{h-pad}" x2="{w-pad}" y2="{h-pad}" stroke="#94a3b8"/>')
    parts.append(f'<line x1="{pad}" y1="{h-pad}" x2="{pad}" y2="{pad}" stroke="#94a3b8"/>')
    parts.append(f'<text x="{w/2}" y="{h-10}" class="axis">Empirical feasibility</text>')
    parts.append(f'<text x="14" y="{pad-16}" class="axis">Theory support</text>')
    for _, r in rows.iterrows():
        empirical_value = finite_score(r.get("empirical_score_final", r.get("empirical_score", 0)))
        theory_value = finite_score(r.get("theory_support_score"))
        if empirical_value is None or theory_value is None:
            continue
        x = pad + (w - 2 * pad) * empirical_value / 100
        y = h - pad - (h - 2 * pad) * theory_value / 100
        radius = 4 + max(0, min(100, float(r["overall_score"]))) / 25
        title = html.escape(f'{r["topic_title"]}: overall {r["overall_score"]}')
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="#2563eb" opacity="0.72"><title>{title}</title></circle>')
    parts.append("</svg>")
    return "\n".join(parts)


PERCENT_DISPLAY_COLUMNS = {
    "overall_score",
    "empirical_score",
    "empirical_score_final",
    "first_pass_empirical_score",
    "second_pass_score",
    "topic_alignment_score",
    "theory_support_score",
    "theory_gap_score",
    "conceptual_bridge_score",
    "innovation_gap_score",
    "paper_quality_pct",
    "paper_relevance_pct",
    "journal_tier_pct",
    "paper_recency_pct",
    "paper_citation_pct",
    "paper_method_pct",
    "paper_mechanism_pct",
}


def display_col_name(col: str) -> str:
    if col in PERCENT_DISPLAY_COLUMNS:
        return f"{col} (%)"
    return col


def fmt_cell(col: str, x) -> str:
    if col in PERCENT_DISPLAY_COLUMNS:
        try:
            v = float(x)
            if np.isfinite(v):
                return f"{v:.2f}%"
        except Exception:
            pass
        return "NA"
    return fmt(x)


def html_table(df: pd.DataFrame, cols: list[str], n: int = 20) -> str:
    if df.empty:
        return "<p>No rows.</p>"
    cols = [c for c in cols if c in df.columns]
    head = "".join(f"<th>{html.escape(display_col_name(c))}</th>" for c in cols)
    body = []
    for _, r in df.head(n).iterrows():
        tds = "".join(f"<td>{fmt_cell(c, r.get(c))}</td>" for c in cols)
        body.append(f"<tr>{tds}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def scoring_method_panel() -> str:
    return """
    <section class="card">
      <h2>Transparent Scoring Rules</h2>
      <p class="note">The literature score is intentionally conservative. Search queries can retrieve candidate papers, but query words do not count as evidence. Only each paper's title, abstract and source are used for relevance and evidence classification.</p>
      <table>
        <thead><tr><th>Dimension</th><th>Rule</th><th>Implication</th></tr></thead>
        <tbody>
          <tr><td>Direct evidence</td><td>Requires both anchors in the paper text: data resource/data asset/accounting recognition/balance-sheet recognition AND corporate reputation/stakeholder/investor/information-environment language.</td><td>If either side is missing, the paper is not direct evidence.</td></tr>
          <tr><td>Bridge evidence</td><td>Broader semantic concept matches such as information assets, intellectual capital, intangible resources, data valuation, or one-sided data/reputation evidence.</td><td>Bridge evidence can raise theory feasibility and innovation-gap scores even when direct evidence is zero.</td></tr>
          <tr><td>Background evidence</td><td>One-sided reputation, generic accounting/disclosure, or method/mechanism evidence that is useful context but not enough to bridge both sides.</td><td>Counts as context, but less than bridge evidence.</td></tr>
          <tr><td>Source tier</td><td>Displayed as 0-100 using coarse tiers: top journals = 100; strong peer-reviewed journals = 75; ordinary journal articles = 50; SSRN/books/chapters/manual-check sources = 25.</td><td>This avoids false precision while still distinguishing broad source quality.</td></tr>
          <tr><td>Relevance</td><td>Displayed as 0-100. Computed from the paper title, abstract and source against candidate variable names, themes and rough-topic terms. Query text is excluded.</td><td>A paper found by a good query can still receive low relevance if its own text does not match.</td></tr>
          <tr><td>Paper quality</td><td>Displayed as 0-100. It combines source tier, recency, log citation signal, method signal, mechanism signal and relevance; books/chapters/working papers are capped.</td><td>High publication quality cannot compensate for missing topical relevance.</td></tr>
          <tr><td>Theory support score</td><td>Aggregates direct evidence, bridge evidence, background density, recency, source tier, methods, mechanisms and query-family coverage.</td><td>Direct evidence is no longer required for a usable theory score when bridge evidence is strong.</td></tr>
          <tr><td>Theory gap score</td><td>Rewards active but not saturated bridge literature. When direct evidence is zero but bridge evidence is dense, the report marks this as a potential innovation gap.</td><td>No direct evidence is treated as a possible contribution opportunity, not merely a weakness.</td></tr>
        </tbody>
      </table>
    </section>
    """


def write_chart_file(outdir: Path, slug: str, title: str, svg: str) -> str:
    chart_dir = outdir / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    path = chart_dir / f"{slug}.html"
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:Inter,Segoe UI,Arial,sans-serif;margin:0;background:#f8fafc;color:#0f172a}}
main{{padding:24px;max-width:1280px;margin:auto}}
.chart{{width:100%;height:auto;background:white;border:1px solid #e5e7eb;border-radius:8px}}
.chart-title{{font-weight:700;font-size:15px;fill:#0f172a}}.axis{{font-size:11px;fill:#475569}}
a{{color:#2563eb}}
</style></head><body><main>
<p><a href="../research_topic_lab_report.html">Back to dashboard</a></p>
{svg}
</main></body></html>"""
    path.write_text(doc, encoding="utf-8")
    return f"charts/{path.name}"


def chart_card(title: str, href: str, svg: str) -> str:
    return f"""<section class="card chart-card">
      <div class="chart-head"><h3>{html.escape(title)}</h3><a href="{html.escape(href)}" target="_blank">Open full chart</a></div>
      <a href="{html.escape(href)}" target="_blank" class="chart-link" title="Open standalone interactive chart page">{svg}</a>
    </section>"""


def render_html(
    outdir: Path,
    data_path: Path,
    ranked: pd.DataFrame,
    profiles: pd.DataFrame,
    lit: pd.DataFrame,
    deep: pd.DataFrame,
    structure: dict,
    args: argparse.Namespace,
    external: pd.DataFrame,
    external_ideas: pd.DataFrame,
    query_diag: pd.DataFrame,
) -> None:
    chart_specs = [
        ("overall_score", "Overall topic feasibility", score_bar(ranked, "overall_score", "Overall topic feasibility", "#2563eb")),
        ("theory_vs_empirical", "Theory vs empirical feasibility", scatter(ranked)),
        (
            "theory_components",
            "Theory evidence components",
            grouped_score_bars(ranked, [("theory_support_score","theory support","#7c3aed"),("theory_gap_score","theory gap","#db2777")], "Theory evidence components"),
        ),
        (
            "empirical_components",
            "Empirical first-pass vs second-pass",
            grouped_score_bars(ranked, [("first_pass_empirical_score","first pass","#ea580c"),("second_pass_score","second pass","#16a34a")], "Empirical first-pass vs second-pass"),
        ),
        ("external_themes", "External data theme coverage", theme_distribution_chart(external)),
    ]
    chart_cards = []
    for slug, title, svg in chart_specs:
        href = write_chart_file(outdir, slug, title, svg)
        chart_cards.append(chart_card(title, href, svg))

    top_cards = []
    for i, r in ranked.head(3).iterrows():
        top_cards.append(
            f"""
            <section class="card">
              <div class="rank">#{i+1} {html.escape(r['feasibility_label'])}</div>
              <h3>{html.escape(str(r['topic_title']))}</h3>
              <p><b>Theory gap:</b> {html.escape(str(r['theory_gap']))}</p>
              <p><b>Mechanism:</b> {html.escape(str(r['mechanism_logic']))}</p>
              <p><b>Scores:</b> overall {fmt(r['overall_score'])}, empirical final {fmt(r['empirical_score_final'])}, first pass {fmt(r['first_pass_empirical_score'])}, second pass {fmt(r['second_pass_score'])}, theory support {fmt(r['theory_support_score'])}, gap {fmt(r['theory_gap_score'])}, topic alignment {fmt(r['topic_alignment_score'])}.</p>
              <p><b>Literature:</b> {html.escape(str(r.get('literature_search_state','not searched')))}; {html.escape(str(r.get('literature_status','')))}</p>
            </section>
            """
        )
    css = """
    body{font-family:Inter,Segoe UI,Arial,sans-serif;margin:0;background:#f8fafc;color:#0f172a}
    header{padding:28px 34px;background:#111827;color:white}
    main{padding:24px 34px;max-width:1200px;margin:auto}
    h1{margin:0 0 8px;font-size:28px} h2{margin-top:28px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
    .card{background:white;border:1px solid #e5e7eb;border-radius:8px;padding:16px;box-shadow:0 1px 2px rgba(15,23,42,.06)}
    .rank{font-size:13px;color:#2563eb;font-weight:700;text-transform:uppercase}
    table{border-collapse:collapse;width:100%;background:white;border:1px solid #e5e7eb}
    th,td{padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:left;font-size:13px;vertical-align:top}
    th{background:#f1f5f9}.chart{width:100%;max-width:880px;background:white;border:1px solid #e5e7eb;border-radius:8px;margin:8px 0}
    .chart-title{font-weight:700;font-size:15px;fill:#0f172a}.axis{font-size:11px;fill:#475569}
    .note{color:#475569;font-size:13px}.pill{display:inline-block;background:#e0f2fe;color:#075985;border-radius:999px;padding:4px 8px;margin:2px;font-size:12px}
    .chart-card h3{margin:0;font-size:15px}.chart-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
    .chart-head a{font-size:12px;color:#2563eb}.chart-link{display:block}
    .warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:8px;padding:12px;margin:12px 0}
    """
    lit_state_counts = ranked.get("literature_search_state", pd.Series(dtype=str)).fillna("not searched").value_counts().to_dict()
    lit_note = ""
    if args.skip_literature:
        lit_note = '<div class="warn"><b>Literature search skipped.</b> Theory scores are shown as NA and should not be interpreted as evidence.</div>'
    elif any(k != "searched" for k in lit_state_counts):
        lit_note = f'<div class="warn"><b>Literature search diagnostics:</b> {html.escape(json.dumps(lit_state_counts, ensure_ascii=False))}. Check the Query Diagnostics table before trusting theory scores.</div>'
    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Research Topic Lab</title><style>{css}</style></head>
<body>
<header>
  <h1>Research Topic Lab</h1>
  <div>Dataset: {html.escape(str(data_path))}</div>
  <div>Rough topic: {html.escape(args.topic or "open brainstorming")}</div>
</header>
<main>
  <section class="card">
    <h2>Detected Data Structure</h2>
    <p>
      <span class="pill">Entity: {html.escape(str(structure.get('id') or 'not detected'))}</span>
      <span class="pill">Time: {html.escape(str(structure.get('time') or 'not detected'))}</span>
      <span class="pill">Outcomes: {len(structure.get('outcomes', []))}</span>
      <span class="pill">Key variables: {len(structure.get('keys', []))}</span>
      <span class="pill">Controls: {len(structure.get('controls', []))}</span>
      <span class="pill">External files profiled: {len(external)}</span>
    </p>
    <p class="note">This is a screening report. It ranks topic feasibility; it does not certify causality or publishability.</p>
  </section>

  <h2>Top Three Topic Directions</h2>
  <div class="grid">{''.join(top_cards)}</div>

  <h2>Visual Score Dashboard</h2>
  {lit_note}
  {scoring_method_panel()}
  <div class="grid">
    {''.join(chart_cards)}
  </div>

  <h2>Ranked Topic Table</h2>
  {html_table(ranked, ["feasibility_label","overall_score","empirical_score_final","first_pass_empirical_score","second_pass_score","topic_alignment_score","theory_support_score","theory_gap_score","conceptual_bridge_score","innovation_gap_score","evidence_profile","literature_search_state","literature_status","raw_literature_hits","relevant_literature_hits","direct_evidence_hits","bridge_evidence_hits","background_evidence_hits","mean_paper_quality","mean_relevance","query_families_with_hits","top_tier_hits","peer_reviewed_hits","method_hits","mechanism_hits","design","outcome","key_variable","coef","se","p","n"], 30)}

  <h2>Second-Pass Validation For Top Topics</h2>
  {html_table(deep, ["topic_title","deep_design","twfe_coef","twfe_p","pretrend_pass","pretrend_min_p","placebo_empirical_p","placebo_reps","second_pass_score","deep_status"], 10)}

  <h2>Literature Evidence</h2>
  {html_table(lit, ["candidate_title","passes_relevance_screen","evidence_class","evidence_reason","text_data_anchor","broad_data_concept_anchor","adjacent_asset_anchor","generic_data_or_disclosure_anchor","text_outcome_anchor","direct_requirements_met","conceptual_bridge_strength_pct","semantic_direction","title","authors","year","source","source_type","journal_tier","paper_quality_pct","paper_relevance_pct","journal_tier_pct","paper_recency_pct","paper_citation_pct","paper_method_pct","paper_mechanism_pct","query_family","query","doi","url","cited_by","is_oa"], 120)}

  <h2>Literature Query Diagnostics</h2>
  <p class="note">This table shows whether each query actually returned usable records. A topic with low or missing theory scores should be judged from this table before drawing conclusions.</p>
  {html_table(query_diag, ["candidate_title","query_family","query","status","raw_hits","valid_hits","relevant_hits","error"], 120)}

  <h2>External Data Expansion Pool</h2>
  <p class="note">These files were scanned from the root directory to broaden topic imagination. Merge-ready files have likely firm and time identifiers; non-merge-ready files are still useful as conceptual prompts but need manual linkage checks.</p>
  {html_table(external, ["file_name","merge_ready","n_columns","id_candidates","time_candidates","outcome_candidates","key_candidates","themes"], 50)}

  <h2>External Topic Ideas</h2>
  {html_table(external_ideas, ["idea_type","ideation_lens","file_name","candidate_variable","merge_ready","theory_anchor","data_action","suggested_topic","themes"], 80)}

  <h2>Variable Profile</h2>
  {html_table(profiles, ["name","role","theme","n","missing_rate","unique","mean","std","min","max"], 80)}
</main>
</body></html>"""
    (outdir / "research_topic_lab_report.html").write_text(html_doc, encoding="utf-8")


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    data_path = Path(args.data).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve() if args.outdir else data_path.with_suffix("").parent / f"{data_path.stem}_research_topic_lab"
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_data(data_path)
    scan_root = Path(args.scan_root).expanduser().resolve() if args.scan_root else data_path.parent
    external = scan_external_data(scan_root, data_path, args.external_max_files)
    external_ideas = external_topic_ideas(external, args.topic)
    external.to_csv(outdir / "external_data_profile.csv", index=False, encoding="utf-8-sig")
    external_ideas.to_csv(outdir / "external_topic_ideas.csv", index=False, encoding="utf-8-sig")
    infos = profile(df)
    structure = detect_structure(infos, args)
    df, structure = add_brainstorm_constructs(df, structure)
    if structure.get("constructed_keys"):
        for key in structure["constructed_keys"]:
            infos.append(
                VarProfile(
                    name=key,
                    dtype=str(df[key].dtype),
                    n=int(df[key].notna().sum()),
                    missing_rate=float(df[key].isna().mean()),
                    unique=int(df[key].nunique(dropna=True)),
                    mean=float(num(df[key]).mean()),
                    std=float(num(df[key]).std()),
                    min=float(num(df[key]).min()),
                    max=float(num(df[key]).max()),
                    role="constructed_treatment",
                    theme="constructed DID treatment",
                )
            )
    profiles = pd.DataFrame([v.__dict__ for v in infos])
    profiles.to_csv(outdir / "variable_profile.csv", index=False, encoding="utf-8-sig")
    candidates = brainstorm(df, infos, structure, args.topic, args.max_candidates)
    if candidates.empty:
        raise SystemExit("No candidate topic could be estimated. Check numeric variables and sample size.")

    lit_summary, lit_records, query_diag = search_literature(candidates, args)
    ranked = merge_scores(candidates, lit_summary)
    deep = deep_validate(df, ranked, structure, args)
    ranked = apply_second_pass_scores(ranked, deep)
    ranked = merge_scores(ranked, pd.DataFrame())

    ranked.to_csv(outdir / "topic_scores.csv", index=False, encoding="utf-8-sig")
    lit_records.to_csv(outdir / "literature_evidence.csv", index=False, encoding="utf-8-sig")
    query_diag.to_csv(outdir / "literature_query_diagnostics.csv", index=False, encoding="utf-8-sig")
    deep.to_csv(outdir / "second_pass_validation.csv", index=False, encoding="utf-8-sig")
    (outdir / "summary.json").write_text(
        json.dumps(
            {
                "data": str(data_path),
                "outdir": str(outdir),
                "n_rows": int(len(df)),
                "n_columns": int(len(df.columns)),
                "structure": structure,
                "external_files_profiled": int(len(external)),
                "top_topics": ranked.head(5).to_dict("records"),
                "literature_search_skipped": bool(args.skip_literature),
                "literature_state_counts": ranked.get("literature_search_state", pd.Series(dtype=str)).fillna("not searched").value_counts().to_dict(),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    render_html(outdir, data_path, ranked, profiles, lit_records, deep, structure, args, external, external_ideas, query_diag)
    checks = validation_checks(outdir, df, ranked, profiles, lit_records, deep, external, query_diag, args)
    print(json.dumps({"outdir": str(outdir), "html": str(outdir / "research_topic_lab_report.html"), "top_topics": ranked.head(3)[["topic_title", "overall_score", "feasibility_label"]].to_dict("records")}, ensure_ascii=False, indent=2))
    if not bool(checks["passed"].all()):
        failed = checks.loc[~checks["passed"], ["function", "detail"]].to_dict("records")
        print(json.dumps({"feature_validation_failed": failed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
