"""
Aristocrat Gaming location scraper.

Usage:
    python scraper.py                          # defaults to GG-382 (Lightning 10 Year Storm)
    python scraper.py "Lightning 10 Year Storm"  # search by game title
    python scraper.py GG-382                   # search by game ID directly
"""

import json
import sys
import os
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "https://www.aristocratgaming.com/us/where-to-play"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def resolve_game_id(page, query: str) -> tuple[str, str]:
    """
    Given a game title or game ID, return (game_id, game_title).
    Raises ValueError if not found.
    """
    game_data = page.evaluate("window.gameData")
    if not game_data:
        raise RuntimeError("window.gameData not available — page may not have loaded correctly.")

    # If it looks like a game ID (e.g. GG-382, GT-123), match directly
    if query.upper().startswith(("GG-", "GT-")):
        game_id = query.upper()
        match = next((g for g in game_data if g.get("custom_s_analytics_id") == game_id), None)
        title = match["title"] if match else game_id
        return game_id, title

    # Otherwise search by title (case-insensitive substring)
    query_lower = query.lower()
    matches = [g for g in game_data if query_lower in g.get("title", "").lower()]
    if not matches:
        raise ValueError(f"No game found matching '{query}'. Check the title or use a game ID like GG-382.")
    if len(matches) > 1:
        options = "\n  ".join(f"{g['custom_s_analytics_id']}: {g['title']}" for g in matches[:10])
        raise ValueError(f"Multiple games match '{query}':\n  {options}\nPlease be more specific.")
    g = matches[0]
    return g["custom_s_analytics_id"], g["title"]


def scrape(query: str = "GG-382") -> list[dict]:
    """
    Scrape casino locations for a given game title or game ID.
    Returns sorted list of {"name": ..., "address": ...} dicts.
    Saves a timestamped snapshot to data/.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Loading page for query: {query}")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait until AristocratLocations is populated
        try:
            page.wait_for_function("window.AristocratLocations && window.AristocratLocations.length > 0", timeout=30000)
        except PlaywrightTimeout:
            raise RuntimeError("Timed out waiting for AristocratLocations to load.")

        game_id, game_title = resolve_game_id(page, query)
        print(f"Game: {game_title} ({game_id})")

        locations = page.evaluate(f"""() => {{
            const gameID = '{game_id}';
            return window.AristocratLocations
                .filter(f => f.properties.GameIDs && f.properties.GameIDs.includes(gameID))
                .map(f => ({{
                    name: f.properties.CasinoName,
                    address: [
                        f.properties.Address,
                        f.properties.City,
                        f.properties.State,
                        f.properties.MailCode
                    ].filter(Boolean).join(', ')
                }}))
                .sort((a, b) => a.name.localeCompare(b.name));
        }}""")

        browser.close()

    print(f"\nFound {len(locations)} locations with {game_title} ({game_id}):\n")
    print(f"{'Casino Name':<60} {'Address'}")
    print("-" * 120)
    for loc in locations:
        print(f"{loc['name']:<60} {loc['address']}")

    # Save snapshot
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
    print(f"\nSnapshot saved to: {filename}")

    return locations


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scraper.py <game name or game ID>")
        print("  python scraper.py \"Lightning 10 Year Storm\"")
        print("  python scraper.py GG-382")
        sys.exit(1)
    scrape(sys.argv[1])
