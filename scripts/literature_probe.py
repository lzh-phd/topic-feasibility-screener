#!/usr/bin/env python
"""Probe literature support for a rough empirical topic via OpenAlex/CrossRef.

This is a lightweight fallback for topic screening. When richer academic-search
MCP tools are available, prefer those. This script gives a quick, reproducible
literature-density and recency check without external Python dependencies.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from pathlib import Path


TOP_SOURCE = re.compile(
    r"^(the journal of finance|journal of finance|journal of accounting research|journal of accounting and economics|"
    r"the accounting review|accounting review|management science|strategic management journal|"
    r"american economic review|quarterly journal of economics|journal of political economy|econometrica)$",
    re.I,
)
STRONG_SOURCE = re.compile(
    r"^(research policy|information systems research|mis quarterly|journal of corporate finance|"
    r"technological forecasting and social change|business strategy and the environment|journal of economic surveys|"
    r"journal of business ethics|journal of consumer psychology)$",
    re.I,
)
BOOK_TYPES = {"book", "book-chapter", "book-part", "monograph"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", required=True, help="Rough research topic")
    p.add_argument("--terms", nargs="*", default=None, help="Extra variables/mechanisms to search")
    p.add_argument("--outdir", required=True, help="Output directory")
    p.add_argument("--per-query", type=int, default=8, help="Results per query")
    p.add_argument("--mailto", default="research@example.com", help="Email for polite OpenAlex requests")
    return p.parse_args()


def fetch_openalex(query: str, per_page: int, mailto: str) -> list[dict]:
    params = {
        "search": query,
        "per-page": str(per_page),
        "mailto": mailto,
    }
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": mailto})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    rows = []
    for item in data.get("results", []):
        loc = item.get("primary_location") or {}
        source = (loc.get("source") or {}).get("display_name")
        rows.append(
            {
                "query": query,
                "provider": "openalex",
                "title": item.get("display_name"),
                "year": item.get("publication_year"),
                "doi": item.get("doi"),
                "source": source,
                "work_type": item.get("type") or "",
                "landing_page_url": loc.get("landing_page_url"),
                "pdf_url": loc.get("pdf_url"),
                "is_oa": (item.get("open_access") or {}).get("is_oa"),
                "cited_by_count": item.get("cited_by_count"),
                "abstract": inverted_abstract(item.get("abstract_inverted_index")),
            }
        )
    return rows


def fetch_crossref(query: str, per_page: int, mailto: str) -> list[dict]:
    params = {"query.bibliographic": query, "rows": str(min(per_page, 20)), "mailto": mailto}
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": f"topic-feasibility-screener mailto:{mailto}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    rows = []
    for item in (data.get("message") or {}).get("items", []):
        year_parts = (((item.get("published-print") or item.get("published-online") or item.get("issued") or {}).get("date-parts")) or [[]])
        rows.append(
            {
                "query": query,
                "provider": "crossref",
                "title": " ".join(item.get("title") or []),
                "year": year_parts[0][0] if year_parts and year_parts[0] else None,
                "doi": item.get("DOI"),
                "source": "; ".join(item.get("container-title") or []),
                "work_type": item.get("type") or "",
                "landing_page_url": item.get("URL"),
                "pdf_url": "",
                "is_oa": "",
                "cited_by_count": item.get("is-referenced-by-count") or 0,
                "abstract": re.sub(r"<[^>]+>", " ", item.get("abstract") or "")[:1200],
            }
        )
    return rows


def inverted_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pairs = []
    for word, positions in inv.items():
        for pos in positions:
            pairs.append((pos, word))
    return " ".join(word for _, word in sorted(pairs))[:1200]


def dedup(rows: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for r in rows:
        key = (r.get("doi") or r.get("title") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def source_type(row: dict) -> str:
    doi = str(row.get("doi") or "").lower()
    src = str(row.get("source") or "").lower()
    work_type = str(row.get("work_type") or "").lower()
    if doi.startswith("10.2139/") or "ssrn" in src:
        return "working/preprint"
    if work_type in BOOK_TYPES or re.search(r"(handbook|book|chapter|monograph)", src):
        return "book/chapter"
    if work_type == "journal-article" or row.get("source"):
        return "journal article"
    return "unknown"


def source_tier(row: dict) -> tuple[str, float]:
    src = str(row.get("source") or "").strip()
    typ = source_type(row)
    if typ in {"working/preprint", "book/chapter"}:
        return typ, 2.0
    if TOP_SOURCE.search(src):
        return "top journal", 22.0
    if STRONG_SOURCE.search(src):
        return "strong peer-reviewed", 14.0
    if typ == "journal article":
        return "journal/manual-tier-check", 7.0
    return "unknown", 1.0


def evidence_class(row: dict, topic: str, terms: list[str]) -> str:
    text = " ".join(str(row.get(k) or "") for k in ["title", "abstract", "source"]).lower()
    topic_low = topic.lower()
    treatment_terms = [t for t in terms if re.search(r"(data|digital|entry|asset|recognition|policy|esg|green|audit|governance|finance)", t.lower())]
    outcome_terms = [t for t in terms if re.search(r"(reputation|score|performance|risk|turnover|forecast|analyst|constraint|innovation)", t.lower())]
    data_anchor = bool(re.search(r"(data asset|data resource|accounting recognition|intangible asset|digital transformation|disclosure|policy)", text))
    outcome_anchor = bool(re.search(r"(reputation|stakeholder|investor|information environment|information efficiency|performance|market reaction)", text))
    if treatment_terms and any(t.lower() in text for t in treatment_terms):
        data_anchor = True
    if outcome_terms and any(t.lower() in text for t in outcome_terms):
        outcome_anchor = True
    if "reputation" in topic_low and "reputation" in text:
        outcome_anchor = True
    if data_anchor and outcome_anchor:
        return "direct_or_close"
    if data_anchor or outcome_anchor:
        return "background"
    return "weak"


def score_row(row: dict, topic: str, terms: list[str]) -> dict:
    tier, tier_score = source_tier(row)
    typ = source_type(row)
    text = " ".join(str(row.get(k) or "") for k in ["title", "abstract", "source"]).lower()
    rel = 0.0
    for token in re.split(r"[^a-z0-9\u4e00-\u9fff]+", topic.lower() + " " + " ".join(terms).lower()):
        if len(token) >= 4 and token in text:
            rel += 1.5
    rel = min(rel, 20.0)
    try:
        year = int(row.get("year") or 0)
    except Exception:
        year = 0
    recency = 8.0 if year >= 2025 else 6.0 if year >= 2023 else 3.0 if year >= 2019 else 1.0 if year else 0.0
    cited = float(row.get("cited_by_count") or 0)
    quality = tier_score + rel + recency + min(10.0, math.log1p(cited) * 2.0)
    if typ in {"working/preprint", "book/chapter"}:
        quality = min(quality, 32.0)
    return {
        "source_type": typ,
        "source_tier": tier,
        "evidence_class": evidence_class(row, topic, terms),
        "relevance_score": round(rel, 2),
        "paper_quality_score": round(min(70.0, quality), 2),
    }


def classify_gap(rows: list[dict]) -> dict:
    valid_rows = [r for r in rows if r.get("year") and not str(r.get("title", "")).startswith("SEARCH_ERROR")]
    errors = [r for r in rows if str(r.get("title", "")).startswith("SEARCH_ERROR")]
    years = [int(r["year"]) for r in valid_rows if r.get("year")]
    recent = [y for y in years if y >= 2024]
    oa = [r for r in valid_rows if r.get("is_oa")]
    density = len(valid_rows)
    direct = [r for r in valid_rows if r.get("evidence_class") == "direct_or_close"]
    background = [r for r in valid_rows if r.get("evidence_class") == "background"]
    top = [r for r in valid_rows if r.get("source_tier") == "top journal"]
    peer = [r for r in valid_rows if r.get("source_type") == "journal article"]
    if len(direct) >= 5 and density >= 20 and len(recent) >= 5:
        status = "active literature; emphasize incremental mechanism, setting, or identification"
    elif len(direct) >= 2 or (len(background) >= 8 and density >= 12):
        status = "moderate literature; feasible if the dataset offers a sharper design or new context"
    elif len(background) >= 3 or density >= 5:
        status = "thin literature; potentially novel but needs stronger theory and careful validation"
    else:
        status = "very thin literature; high novelty risk and high framing burden"
    if density == 0 and errors:
        status = "search failed or returned no valid records; retry with academic-search MCP, CrossRef, Semantic Scholar, or broader keywords"
    return {
        "total_hits_collected": density,
        "search_errors": len(errors),
        "recent_2024_plus": len(recent),
        "open_access_hits": len(oa),
        "direct_or_close_hits": len(direct),
        "background_hits": len(background),
        "top_journal_hits": len(top),
        "journal_article_hits": len(peer),
        "earliest_year": min(years) if years else None,
        "latest_year": max(years) if years else None,
        "literature_status": status,
    }


def write_outputs(outdir: Path, topic: str, rows: list[dict], summary: dict) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "literature_probe.csv"
    fields = ["provider", "query", "title", "year", "doi", "source", "work_type", "source_type", "source_tier", "evidence_class", "relevance_score", "paper_quality_score", "landing_page_url", "pdf_url", "is_oa", "cited_by_count", "abstract"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    (outdir / "literature_probe_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Literature feasibility probe",
        "",
        f"Topic: {topic}",
        "",
        "## Summary",
        "",
        f"- Total records collected: {summary['total_hits_collected']}",
        f"- Search errors: {summary.get('search_errors', 0)}",
        f"- Recent records from 2024 onward: {summary['recent_2024_plus']}",
        f"- Direct/close evidence records: {summary['direct_or_close_hits']}",
        f"- Background records: {summary['background_hits']}",
        f"- Top-journal records: {summary['top_journal_hits']}",
        f"- Open-access records: {summary['open_access_hits']}",
        f"- Literature status: {summary['literature_status']}",
        "",
        "## Most relevant records",
        "",
    ]
    valid_rows = [r for r in rows if r.get("year") and not str(r.get("title", "")).startswith("SEARCH_ERROR")]
    for i, r in enumerate(valid_rows[:20], start=1):
        lines.append(f"{i}. {r.get('title')} ({r.get('year')})")
        lines.append(f"   - Source: {r.get('source') or 'unknown'}")
        lines.append(f"   - DOI/link: {r.get('doi') or r.get('landing_page_url') or 'not available'}")
        if r.get("abstract"):
            lines.append(f"   - Abstract signal: {r['abstract'][:240]}...")
        lines.append("")
    (outdir / "literature_probe_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    terms = args.terms or []
    queries = [
        args.topic,
        f"{args.topic} empirical evidence",
        f"{args.topic} theory mechanism",
        f"{args.topic} causal identification",
    ]
    for term in terms[:8]:
        queries.append(f"{args.topic} {term}")

    rows: list[dict] = []
    diagnostics = []
    for q in queries:
        for provider, fetcher in [("openalex", fetch_openalex), ("crossref", fetch_crossref)]:
            diag = {"provider": provider, "query": q, "status": "ok", "raw_hits": 0, "error": ""}
            try:
                got = fetcher(q, args.per_query, args.mailto)
                rows.extend(got)
                diag["raw_hits"] = len(got)
            except HTTPError as exc:
                diag["status"] = "rate_limited" if exc.code == 429 else "error"
                diag["error"] = f"HTTP {exc.code}: {exc.reason}"
                rows.append({"provider": provider, "query": q, "title": f"SEARCH_ERROR: {exc}", "year": None})
            except Exception as exc:
                diag["status"] = "error"
                diag["error"] = str(exc)
                rows.append({"provider": provider, "query": q, "title": f"SEARCH_ERROR: {exc}", "year": None})
            diagnostics.append(diag)
            time.sleep(0.25)
    rows = dedup(rows)
    for r in rows:
        if r.get("year"):
            r.update(score_row(r, args.topic, terms))
    rows.sort(key=lambda r: (r.get("year") or 0, r.get("cited_by_count") or 0), reverse=True)
    summary = classify_gap(rows)
    summary["query_diagnostics"] = diagnostics
    write_outputs(Path(args.outdir), args.topic, rows, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
