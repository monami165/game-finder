"""
Compare two snapshots to identify new and removed casino installations.

Usage:
    python compare.py data/GG382_2026-05-31_10-00-00.json data/GG382_2026-06-07_10-00-00.json
"""

import json
import sys
import os
from datetime import datetime


def load_snapshot(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compare_snapshots(path_a: str, path_b: str) -> dict:
    """
    Compare two snapshot files. Returns a dict with:
        new_installations  - locations in B but not in A (newly added)
        removed            - locations in A but not in B (no longer listed)
        unchanged          - locations in both
    Locations are matched by (name, address) pair.
    """
    snap_a = load_snapshot(path_a)
    snap_b = load_snapshot(path_b)

    def key(loc):
        return (loc["name"].strip().upper(), loc["address"].strip().upper())

    set_a = {key(loc): loc for loc in snap_a["locations"]}
    set_b = {key(loc): loc for loc in snap_b["locations"]}

    keys_a = set(set_a)
    keys_b = set(set_b)

    new_installations = sorted([set_b[k] for k in keys_b - keys_a], key=lambda x: x["name"])
    removed = sorted([set_a[k] for k in keys_a - keys_b], key=lambda x: x["name"])
    unchanged = sorted([set_b[k] for k in keys_a & keys_b], key=lambda x: x["name"])

    return {
        "game_id": snap_b.get("game_id", snap_a.get("game_id")),
        "game_title": snap_b.get("game_title", snap_a.get("game_title")),
        "snapshot_a": {"file": os.path.basename(path_a), "scraped_at": snap_a.get("scraped_at"), "total": len(snap_a["locations"])},
        "snapshot_b": {"file": os.path.basename(path_b), "scraped_at": snap_b.get("scraped_at"), "total": len(snap_b["locations"])},
        "new_installations": new_installations,
        "removed": removed,
        "unchanged": unchanged,
    }


COMPARE_DIR = os.path.join(os.path.dirname(__file__), "compare")


def build_report_lines(result: dict) -> list[str]:
    game = f"{result['game_title']} ({result['game_id']})"
    a = result["snapshot_a"]
    b = result["snapshot_b"]
    new = result["new_installations"]
    removed = result["removed"]

    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"  Comparison Report: {game}")
    lines.append(f"{'='*70}")
    lines.append(f"  Older snapshot : {a['file']}  ({a['scraped_at']})  — {a['total']} locations")
    lines.append(f"  Newer snapshot : {b['file']}  ({b['scraped_at']})  — {b['total']} locations")
    lines.append(f"{'='*70}\n")

    if new:
        lines.append(f"NEW INSTALLATIONS ({len(new)}):")
        lines.append(f"  {'Casino Name':<55} Address")
        lines.append(f"  {'-'*110}")
        for loc in new:
            lines.append(f"  {loc['name']:<55} {loc['address']}")
    else:
        lines.append("NEW INSTALLATIONS: none")

    lines.append("")

    if removed:
        lines.append(f"REMOVED ({len(removed)}):")
        lines.append(f"  {'Casino Name':<55} Address")
        lines.append(f"  {'-'*110}")
        for loc in removed:
            lines.append(f"  {loc['name']:<55} {loc['address']}")
    else:
        lines.append("REMOVED: none")

    lines.append(f"\nUNCHANGED: {len(result['unchanged'])} locations\n")
    return lines


def print_report(result: dict):
    lines = build_report_lines(result)
    for line in lines:
        print(line)

    os.makedirs(COMPARE_DIR, exist_ok=True)
    safe_id = result["game_id"].replace("-", "")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(COMPARE_DIR, f"{safe_id}_compare_{timestamp}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report saved to: {filename}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare.py <snapshot_a.json> <snapshot_b.json>")
        print("\nAvailable snapshots in data/:")
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        if os.path.isdir(data_dir):
            for f in sorted(os.listdir(data_dir)):
                if f.endswith(".json"):
                    print(f"  data/{f}")
        sys.exit(1)

    result = compare_snapshots(sys.argv[1], sys.argv[2])
    print_report(result)
