#!/usr/bin/env python
"""Probe literature support for a rough empirical topic via OpenAlex.

This is a lightweight fallback for topic screening. When richer academic-search
MCP tools are available, prefer those. This script gives a quick, reproducible
literature-density and recency check without external Python dependencies.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


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
                "title": item.get("display_name"),
                "year": item.get("publication_year"),
                "doi": item.get("doi"),
                "source": source,
                "landing_page_url": loc.get("landing_page_url"),
                "pdf_url": loc.get("pdf_url"),
                "is_oa": (item.get("open_access") or {}).get("is_oa"),
                "cited_by_count": item.get("cited_by_count"),
                "abstract": inverted_abstract(item.get("abstract_inverted_index")),
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


def classify_gap(rows: list[dict]) -> dict:
    valid_rows = [r for r in rows if r.get("year") and not str(r.get("title", "")).startswith("SEARCH_ERROR")]
    errors = [r for r in rows if str(r.get("title", "")).startswith("SEARCH_ERROR")]
    years = [int(r["year"]) for r in valid_rows if r.get("year")]
    recent = [y for y in years if y >= 2024]
    oa = [r for r in valid_rows if r.get("is_oa")]
    density = len(valid_rows)
    if density >= 20 and len(recent) >= 5:
        status = "active literature; emphasize incremental mechanism, setting, or identification"
    elif density >= 8:
        status = "moderate literature; feasible if the dataset offers a sharper design or new context"
    elif density >= 3:
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
        "earliest_year": min(years) if years else None,
        "latest_year": max(years) if years else None,
        "literature_status": status,
    }


def write_outputs(outdir: Path, topic: str, rows: list[dict], summary: dict) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "literature_probe.csv"
    fields = ["query", "title", "year", "doi", "source", "landing_page_url", "pdf_url", "is_oa", "cited_by_count", "abstract"]
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
    for q in queries:
        try:
            rows.extend(fetch_openalex(q, args.per_query, args.mailto))
        except Exception as exc:
            rows.append({"query": q, "title": f"SEARCH_ERROR: {exc}", "year": None})
        time.sleep(0.25)
    rows = dedup(rows)
    rows.sort(key=lambda r: (r.get("year") or 0, r.get("cited_by_count") or 0), reverse=True)
    summary = classify_gap(rows)
    write_outputs(Path(args.outdir), args.topic, rows, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
