#!/usr/bin/env python3
"""Check source freshness, link validity, and license status."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, discover_pages, load_data
except ImportError:
    from common import ROOT, discover_pages, load_data


def check_url(url: str, timeout: int = 10) -> dict[str, Any]:
    """Perform HEAD request and return status info."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Macawiki-freshness-check/0.3")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"url": url, "status": resp.status, "redirected": resp.url != url, "error": None}
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "redirected": False, "error": str(e)}
    except urllib.error.URLError as e:
        return {"url": url, "status": None, "redirected": False, "error": str(e.reason)}
    except Exception as e:
        return {"url": url, "status": None, "redirected": False, "error": str(e)}


def check_freshness(
    freshness_days: int = 180,
    timeout: int = 10,
) -> dict[str, Any]:
    source_pages = [p for p in discover_pages() if str(p.metadata.get("type", "")).startswith("source-")]

    issues: list[dict[str, Any]] = []
    checked = 0
    ok = 0

    for p in source_pages:
        page_id = str(p.metadata.get("id", "?"))
        url = str(p.metadata.get("url", ""))
        retrieved_at = str(p.metadata.get("retrieved_at", ""))
        license_status = str(p.metadata.get("license_status", ""))

        item = {
            "id": page_id,
            "url": url,
            "title": p.metadata.get("title", ""),
            "issues": [],
        }

        # Check URL accessibility
        if url:
            result = check_url(url, timeout=timeout)
            checked += 1
            if result["error"] or (result["status"] and result["status"] >= 400):
                item["issues"].append(f"URL unreachable: {result.get('error') or result['status']}")
            elif result["redirected"]:
                item["issues"].append(f"URL redirected to: {result['url']}")
            else:
                ok += 1
        else:
            item["issues"].append("No URL in metadata")

        # Check retrieval date freshness
        if retrieved_at:
            try:
                dt = date.fromisoformat(retrieved_at)
                age = (date.today() - dt).days
                if age > freshness_days:
                    item["issues"].append(f"Stale retrieval: {age} days old (threshold: {freshness_days})")
            except (ValueError, TypeError):
                item["issues"].append(f"Invalid retrieval date: {retrieved_at}")
        else:
            item["issues"].append("No retrieval date")

        # Check license status
        if license_status in ("unknown", ""):
            item["issues"].append(f"License status: {license_status or 'missing'}")

        if item["issues"]:
            issues.append(item)

    total = len(source_pages)
    fresh_ratio = (total - len([i for i in issues if any("Stale" in iss or "No retrieval" in iss for iss in i["issues"])])) / total if total > 0 else 0

    return {
        "total_sources": total,
        "urls_checked": checked,
        "urls_reachable": ok,
        "issues_count": len(issues),
        "issues": issues,
        "freshness_ratio": round(fresh_ratio, 3),
        "freshness_window_days": freshness_days,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freshness-days", type=int, default=180, help="Max age of source retrieval (default: 180)")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP request timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--skip-url-check", action="store_true", help="Skip HTTP URL checks (offline mode)")
    args = parser.parse_args()

    timeout = args.timeout

    if args.skip_url_check:
        # Offline mode: only check dates and licenses, skip HTTP
        source_pages = [p for p in discover_pages() if str(p.metadata.get("type", "")).startswith("source-")]
        issues: list[dict[str, Any]] = []
        for p in source_pages:
            page_id = str(p.metadata.get("id", "?"))
            item = {"id": page_id, "title": p.metadata.get("title", ""), "url": p.metadata.get("url", ""), "issues": []}
            retrieved_at = str(p.metadata.get("retrieved_at", ""))
            if retrieved_at:
                try:
                    dt = date.fromisoformat(retrieved_at)
                    age = (date.today() - dt).days
                    if age > args.freshness_days:
                        item["issues"].append(f"Stale: {age} days old")
                except (ValueError, TypeError):
                    item["issues"].append(f"Invalid date: {retrieved_at}")
            else:
                item["issues"].append("No retrieval date")
            license_status = str(p.metadata.get("license_status", ""))
            if license_status in ("unknown", ""):
                item["issues"].append(f"License: {license_status or 'missing'}")
            if item["issues"]:
                issues.append(item)

        report = {
            "total_sources": len(source_pages),
            "urls_checked": 0,
            "urls_reachable": 0,
            "issues_count": len(issues),
            "issues": issues,
            "freshness_ratio": 0.0,
            "freshness_window_days": args.freshness_days,
            "offline": True,
        }
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"=== Source Freshness (offline) ===")
            for item in issues:
                print(f"  {item['id']}: {', '.join(item['issues'])}")
            if not issues:
                print("  All sources fresh.")
        return 1 if issues else 0

    report = check_freshness(freshness_days=args.freshness_days, timeout=timeout)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"=== Source Freshness Check ===")
        print(f"Sources: {report['total_sources']} total, {report['urls_checked']} URLs checked, {report['urls_reachable']} reachable")
        print(f"Freshness ratio: {report['freshness_ratio']:.1%} (window: {report['freshness_window_days']} days)")
        if report["issues"]:
            print(f"\nIssues ({report['issues_count']}):")
            for item in report["issues"]:
                print(f"  [{item['id']}]")
                for issue in item["issues"]:
                    print(f"    - {issue}")
        else:
            print("\nAll sources fresh and reachable.")

    return 1 if report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
