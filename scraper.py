"""
Aristocrat Gaming location scraper.

Usage:
    python scraper.py                            # defaults to GG-382 (Lightning 10 Year Storm)
    python scraper.py "Lightning 10 Year Storm"    # search by game title
    python scraper.py GG-382                     # search by game ID directly
    python scraper.py --watchlist                # check every game in games_list.json,
                                                   # save a snapshot for each, and write a
                                                   # changelog of what changed to compare/
    python scraper.py --watchlist my_list.json    # use a custom watchlist file

Talks directly to the site's data APIs instead of driving a headless browser:
  - Game title <-> game ID (GT-xxx/GG-xxx) lookup comes from Aristocrat's
    Adobe Commerce Live Search GraphQL endpoint (paginated through all games).
  - Casino locations come from the static wtpJson.json GeoJSON feed.
"""

import json
import sys
import os
import glob
from datetime import datetime
import requests

SCRIPT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
COMPARE_DIR = os.path.join(SCRIPT_DIR, "compare")
DEFAULT_WATCHLIST_PATH = os.path.join(SCRIPT_DIR, "games_list.json")

LOCATIONS_URL = (
    "https://delivery-p181405-e2101004.adobeaemcloud.com/adobe/assets/"
    "urn:aaid:aem:069efc24-b2ad-4eab-b445-f954f4508d9b/renditions/original/as/wtpJson.json"
)

GRAPHQL_URL = "https://na1.api.commerce.adobe.com/9TdQSjV54rLH9Et2dSyxkx/graphql"

GRAPHQL_QUERY = """
query productSearch(
  $phrase: String!
  $pageSize: Int
  $currentPage: Int = 1
  $filter: [SearchClauseInput!]
  $sort: [ProductSearchSortInput!]
  $context: QueryContextInput
) {
  productSearch(
    phrase: $phrase
    page_size: $pageSize
    current_page: $currentPage
    filter: $filter
    sort: $sort
    context: $context
  ) {
    total_count
    items {
      productView {
        sku
        name
        attributes {
          name
          value
        }
      }
    }
    page_info {
      current_page
      page_size
      total_pages
    }
  }
}
"""

HEADERS = {
    "content-type": "application/json",
    "ac-scope-locale": "en-US",
    "ac-source-locale": "en-US",
    "referer": "https://www.aristocratgaming.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    # Guest customer group hash, consistently used by the storefront for
    # unauthenticated visitors.
    "magento-customer-group": "b6589fc6ab0dc82cf12099d1c2d40ab994e8410c",
}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_all_games() -> list[dict]:
    """
    Page through the Live Search API and return a list of
    {"game_id": ..., "title": ...} for every game in the catalog.
    """
    games = []
    page = 1
    page_size = 100
    total_pages = None

    while total_pages is None or page <= total_pages:
        variables = {
            "phrase": "",
            "currentPage": page,
            "pageSize": page_size,
            "sort": [{"attribute": "launch_date", "direction": "DESC"}],
            "filter": [],
        }
        resp = requests.get(
            GRAPHQL_URL,
            params={"query": GRAPHQL_QUERY, "variables": json.dumps(variables)},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data and not data.get("data"):
            raise RuntimeError(f"GraphQL error: {data['errors']}")

        search = data["data"]["productSearch"]
        total_pages = search["page_info"]["total_pages"]

        for item in search["items"]:
            pv = item["productView"]
            analytics_id = None
            for attr in pv.get("attributes", []):
                if attr["name"] == "analytics_id":
                    analytics_id = attr["value"]
                    break
            if analytics_id:
                games.append({"game_id": analytics_id, "title": pv["name"]})

        page += 1

    return games


def fetch_locations() -> list[dict]:
    """Fetch and return the raw list of location features from wtpJson.json."""
    resp = requests.get(LOCATIONS_URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["features"]


def resolve_game_id(games: list[dict], query: str) -> tuple[str, str]:
    """
    Given a game title or game ID, return (game_id, game_title).
    Raises ValueError if not found or ambiguous.
    """
    if query.upper().startswith(("GG-", "GT-")):
        game_id = query.upper()
        match = next((g for g in games if g["game_id"] == game_id), None)
        title = match["title"] if match else game_id
        return game_id, title

    query_lower = query.lower()
    matches = [g for g in games if query_lower in g["title"].lower()]
    if not matches:
        raise ValueError(f"No game found matching '{query}'. Check the title or use a game ID like GG-382.")
    if len(matches) > 1:
        options = "\n  ".join(f"{g['game_id']}: {g['title']}" for g in matches[:10])
        raise ValueError(f"Multiple games match '{query}':\n  {options}\nPlease be more specific.")
    g = matches[0]
    return g["game_id"], g["title"]


def filter_locations_for_game(features: list[dict], game_id: str) -> list[dict]:
    """Return sorted [{'name':..., 'address':...}] for the given game ID."""
    locations = []
    for f in features:
        props = f.get("properties", {})
        game_ids = props.get("GameIDs") or []
        if game_id in game_ids:
            address = ", ".join(
                filter(None, [
                    props.get("Address"),
                    props.get("City"),
                    props.get("State"),
                    props.get("MailCode"),
                ])
            )
            locations.append({"name": props.get("CasinoName"), "address": address})
    locations.sort(key=lambda x: (x["name"] or ""))
    return locations


# ---------------------------------------------------------------------------
# Snapshot storage / comparison
# ---------------------------------------------------------------------------

def save_snapshot(game_id: str, game_title: str, locations: list[dict]) -> str:
    """Save a timestamped snapshot to data/ and return its filepath."""
    os.makedirs(DATA_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_id = game_id.replace("-", "")
    filename = os.path.join(DATA_DIR, f"{safe_id}_{timestamp}.json")
    snapshot = {
        "scraped_at": datetime.now().isoformat(),
        "game_id": game_id,
        "game_title": game_title,
        "locations": locations,
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    return filename


def find_latest_snapshot(game_id: str) -> dict | None:
    """Return the most recent previously-saved snapshot dict for game_id, or None."""
    safe_id = game_id.replace("-", "")
    pattern = os.path.join(DATA_DIR, f"{safe_id}_*.json")
    matches = sorted(glob.glob(pattern))  # timestamp format sorts correctly as strings
    if not matches:
        return None
    with open(matches[-1], "r", encoding="utf-8") as f:
        return json.load(f)


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


# ---------------------------------------------------------------------------
# Single game lookup (original CLI behavior)
# ---------------------------------------------------------------------------

def scrape(query: str = "GG-382") -> list[dict]:
    """
    Look up casino locations for a single game title or game ID, print them,
    and save a snapshot. Returns the sorted list of locations.
    """
    print("Fetching game catalog...")
    games = fetch_all_games()
    print(f"Loaded {len(games)} games")

    game_id, game_title = resolve_game_id(games, query)
    print(f"Game: {game_title} ({game_id})")

    print("Fetching location data...")
    features = fetch_locations()
    locations = filter_locations_for_game(features, game_id)

    print(f"\nFound {len(locations)} locations with {game_title} ({game_id}):\n")
    print(f"{'Casino Name':<60} {'Address'}")
    print("-" * 120)
    for loc in locations:
        print(f"{loc['name']:<60} {loc['address']}")

    filename = save_snapshot(game_id, game_title, locations)
    print(f"\nSnapshot saved to: {filename}")

    return locations


# ---------------------------------------------------------------------------
# Watchlist mode
# ---------------------------------------------------------------------------

def load_watchlist(path: str) -> list[str]:
    """
    Load a watchlist file: a JSON array of game titles and/or game IDs, e.g.

        [
          "GG-382",
          "Lightning 10 Year Storm",
          "NFL Super Grand Champions"
        ]

    Creates a starter file with an example entry if none exists yet.
    """
    if not os.path.exists(path):
        starter = ["GG-382"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(starter, f, indent=2)
        print(f"No watchlist found — created a starter file at: {path}")
        print("Edit it (add/remove game titles or IDs) and run --watchlist again.\n")
        return starter

    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    if not isinstance(entries, list) or not all(isinstance(e, str) for e in entries):
        raise ValueError(f"{path} must be a JSON array of strings (game titles or IDs).")

    return entries


def run_watchlist(watchlist_path: str = DEFAULT_WATCHLIST_PATH) -> None:
    """
    Check every game in the watchlist file, save a snapshot for each, compare
    against each game's previous snapshot, and write a changelog summarizing
    what changed.
    """
    entries = load_watchlist(watchlist_path)
    if not entries:
        print("Watchlist is empty — nothing to do.")
        return

    print("Fetching game catalog...")
    games = fetch_all_games()
    print(f"Loaded {len(games)} games")

    print("Fetching location data...")
    features = fetch_locations()

    changelog_sections = []
    summary_lines = []

    for entry in entries:
        try:
            game_id, game_title = resolve_game_id(games, entry)
        except ValueError as e:
            summary_lines.append(f"  ⚠ '{entry}': {e}")
            changelog_sections.append(f"### '{entry}'\nERROR: {e}\n")
            continue

        new_locations = filter_locations_for_game(features, game_id)
        previous_snapshot = find_latest_snapshot(game_id)

        if previous_snapshot is None:
            save_snapshot(game_id, game_title, new_locations)
            summary_lines.append(
                f"  🆕 {game_title} ({game_id}): first snapshot saved, "
                f"{len(new_locations)} location(s) — nothing to compare yet"
            )
            changelog_sections.append(
                f"### {game_title} ({game_id})\n"
                f"First snapshot saved — {len(new_locations)} location(s). "
                f"No previous data to compare against.\n"
            )
            continue

        old_locations = previous_snapshot.get("locations", [])
        diff = diff_locations(old_locations, new_locations)
        save_snapshot(game_id, game_title, new_locations)

        if not diff["added"] and not diff["removed"]:
            summary_lines.append(f"  ✅ {game_title} ({game_id}): no changes")
            changelog_sections.append(f"### {game_title} ({game_id})\nNo changes.\n")
            continue

        summary_lines.append(
            f"  🔄 {game_title} ({game_id}): "
            f"+{len(diff['added'])} added, -{len(diff['removed'])} removed"
        )

        section_lines = [f"### {game_title} ({game_id})"]
        if diff["added"]:
            section_lines.append(f"Added ({len(diff['added'])}):")
            for loc in diff["added"]:
                section_lines.append(f"  + {loc['name']} — {loc['address']}")
        if diff["removed"]:
            section_lines.append(f"Removed ({len(diff['removed'])}):")
            for loc in diff["removed"]:
                section_lines.append(f"  - {loc['name']} — {loc['address']}")
        changelog_sections.append("\n".join(section_lines) + "\n")

    # Print quick summary
    print(f"\nWatchlist check complete ({len(entries)} game(s)):\n")
    print("\n".join(summary_lines))

    # Save changelog file
    os.makedirs(COMPARE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    changelog_path = os.path.join(COMPARE_DIR, f"changelog_{timestamp}.txt")
    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(f"Watchlist changelog — {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        f.write("\n".join(changelog_sections))

    print(f"\nChangelog saved to: {changelog_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scraper.py <game name or game ID>")
        print("  python scraper.py \"Lightning 10 Year Storm\"")
        print("  python scraper.py GG-382")
        print("  python scraper.py --watchlist [path/to/games_list.json]")
        sys.exit(1)

    if sys.argv[1] == "--watchlist":
        list_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_WATCHLIST_PATH
        run_watchlist(list_path)
    else:
        scrape(sys.argv[1])