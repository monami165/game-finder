"""
Manually compare two saved snapshot files and report location differences.

Usage:
    python compare.py data\\GG382_2026-05-31_10-00-00.json data\\GG382_2026-06-07_10-00-00.json

Prints the diff and also saves a copy to compare\\.
"""

import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(__file__)
COMPARE_DIR = os.path.join(SCRIPT_DIR, "compare")


def diff_locations(old_locations: list[dict], new_locations: list[dict]) -> dict:
    """Return {'added': [...], 'removed': [...]} comparing by (name, address)."""
    old_set = {(l["name"], l["address"]) for l in old_locations}
    new_set = {(l["name"], l["address"]) for l in new_locations}

    added = sorted(
        [{"name": n, "address": a} for (n, a) in (new_set - old_set)],
        key=lambda x: x["name"] or "",
    )
    removed = sorted(
        [{"name": n, "address": a} for (n, a) in (old_set - new_set)],
        key=lambda x: x["name"] or "",
    )
    return {"added": added, "removed": removed}


def main():
    if len(sys.argv) != 3:
        print("Usage: python compare.py <older_snapshot.json> <newer_snapshot.json>")
        sys.exit(1)

    old_path, new_path = sys.argv[1], sys.argv[2]

    with open(old_path, "r", encoding="utf-8") as f:
        old_snapshot = json.load(f)
    with open(new_path, "r", encoding="utf-8") as f:
        new_snapshot = json.load(f)

    old_title = old_snapshot.get("game_title", "?")
    old_id = old_snapshot.get("game_id", "?")
    new_title = new_snapshot.get("game_title", "?")
    new_id = new_snapshot.get("game_id", "?")

    if old_id != new_id:
        print(
            f"WARNING: snapshots are for different games "
            f"({old_title} [{old_id}] vs {new_title} [{new_id}]). Comparing anyway."
        )

    diff = diff_locations(old_snapshot.get("locations", []), new_snapshot.get("locations", []))

    lines = []
    lines.append(f"Comparing snapshots for {new_title} ({new_id})")
    lines.append(f"  Older: {old_path}  ({old_snapshot.get('scraped_at', '?')})")
    lines.append(f"  Newer: {new_path}  ({new_snapshot.get('scraped_at', '?')})")
    lines.append("")

    if not diff["added"] and not diff["removed"]:
        lines.append("No changes.")
    else:
        if diff["added"]:
            lines.append(f"Added ({len(diff['added'])}):")
            for loc in diff["added"]:
                lines.append(f"  + {loc['name']} — {loc['address']}")
        if diff["removed"]:
            lines.append(f"Removed ({len(diff['removed'])}):")
            for loc in diff["removed"]:
                lines.append(f"  - {loc['name']} — {loc['address']}")

    output = "\n".join(lines)
    print(output)

    os.makedirs(COMPARE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_id = new_id.replace("-", "")
    out_path = os.path.join(COMPARE_DIR, f"compare_{safe_id}_{timestamp}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"\nSaved to: {out_path}")


if __name__ == "__main__":
    main()