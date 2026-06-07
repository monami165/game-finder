# Game Finder

Scrapes [Aristocrat Gaming's "Where to Play"](https://www.aristocratgaming.com/us/where-to-play) page to list all casino locations where a specific slot machine game is installed. Saves timestamped snapshots and can compare two snapshots to identify newly installed machines.

---

## Requirements

- Python 3.8+

### Installing Python

**Windows**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download and run the installer
3. ⚠️ On the first screen, check **"Add Python to PATH"** before clicking Install

**Mac**
Option A — Python website (recommended for beginners):
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download and run the `.pkg` installer

Option B — Homebrew (recommended if you already use Homebrew):
```bash
brew install python
```

---

## Getting Started

### Windows
1. Clone this repo
2. Double-click **`start.bat`**

### Mac
1. Clone this repo
2. Open Terminal and make the script executable (one-time step):
   ```bash
   chmod +x start.command
   ```
3. Double-click **`start.command`**

> On first launch, the script automatically creates a virtual environment, installs all dependencies, and downloads the Playwright browser (Chromium). On every subsequent launch it skips setup and goes straight to the menu.

---

## Menu Options

```
===========================================
 Aristocrat Gaming - Game Finder
===========================================

  1. Create location list for a game
  2. Compare two snapshots
  3. Exit
```

**Option 1 — Create location list**
Type a game name (partial, case-insensitive) or a game ID:
```
Lightning 10 Year Storm
GG-382
```
Prints all casino locations sorted A–Z and saves a snapshot to the `data/` folder.

**Option 2 — Compare two snapshots**
Lists available snapshots in `data/`, then prompts for an older and a newer file:
```
Enter OLDER snapshot: data\GG382_2026-05-31_10-00-00.json
Enter NEWER snapshot: data\GG382_2026-06-07_10-00-00.json
```
Reports new installations, removed locations, and unchanged count. The report is also saved as a `.txt` file in the `compare/` folder.

---

## Snapshot format

Each saved file looks like this:

```json
{
  "scraped_at": "2026-05-31T10:00:00",
  "game_id": "GG-382",
  "game_title": "Lightning 10 Year Storm",
  "locations": [
    { "name": "ARIA RESORT AND CASINO", "address": "3730 LAS VEGAS BLVD S, LAS VEGAS, NV, 89158-4300" },
    ...
  ]
}
```

---

## Tracking new installs over time

1. Run option 1 to generate a snapshot.
2. Run option 1 again at a later date.
3. Run option 2 and select the two files to see what changed.
