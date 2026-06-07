#!/bin/bash

# Change to the directory where this script lives
cd "$(dirname "$0")"

# ── Setup (only runs on first launch) ────────────────────────────────────────
if [ ! -f ".venv/bin/activate" ]; then
    echo "Setting up for the first time. This may take a few minutes..."
    echo

    if ! command -v python3 &>/dev/null; then
        echo "ERROR: Python 3 is not installed."
        echo "Install it from https://www.python.org/downloads/ or via Homebrew:"
        echo "  brew install python"
        read -p "Press Enter to exit..."
        exit 1
    fi

    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        read -p "Press Enter to exit..."
        exit 1
    fi

    source .venv/bin/activate
    pip install -r requirements.txt --quiet
    playwright install chromium
    echo
    echo "Setup complete!"
else
    source .venv/bin/activate
fi

# ── Main menu loop ────────────────────────────────────────────────────────────
while true; do
    clear
    echo
    echo " ==========================================="
    echo "  Aristocrat Gaming - Game Finder"
    echo " ==========================================="
    echo
    echo "  1. Create location list for a game"
    echo "  2. Compare two snapshots"
    echo "  3. Exit"
    echo
    echo " ==========================================="
    echo
    read -p " Select an option (1, 2, or 3): " choice

    case "$choice" in

    # ── Option 1: Create list ─────────────────────────────────────────────────
    1)
        while true; do
            clear
            echo
            echo " ==========================================="
            echo "  Create Location List"
            echo " ==========================================="
            echo
            read -p " Enter game name or ID: " game
            if [ -z "$game" ]; then
                echo " No input provided."
                sleep 2
            else
                echo
                python scraper.py "$game"
                echo
                read -p "Press Enter to return to the menu..."
                break
            fi
        done
        ;;

    # ── Option 2: Compare snapshots ───────────────────────────────────────────
    2)
        clear
        echo
        echo " ==========================================="
        echo "  Compare Snapshots"
        echo " ==========================================="
        echo

        if [ ! -d "data" ] || [ -z "$(ls data/*.json 2>/dev/null)" ]; then
            echo " No snapshots found. Run option 1 first to generate a list."
            echo
            read -p "Press Enter to return to the menu..."
            continue
        fi

        echo " Available snapshots:"
        echo
        for f in data/*.json; do
            echo "   $f"
        done
        echo

        while true; do
            read -p " Enter OLDER snapshot: " file_a
            if [ -z "$file_a" ]; then
                echo " No file entered."; sleep 2; continue
            fi
            if [ ! -f "$file_a" ]; then
                echo " File not found: $file_a"; sleep 2; continue
            fi
            break
        done

        while true; do
            read -p " Enter NEWER snapshot: " file_b
            if [ -z "$file_b" ]; then
                echo " No file entered."; sleep 2; continue
            fi
            if [ ! -f "$file_b" ]; then
                echo " File not found: $file_b"; sleep 2; continue
            fi
            break
        done

        echo
        python compare.py "$file_a" "$file_b"
        echo
        read -p "Press Enter to return to the menu..."
        ;;

    # ── Option 3: Exit ────────────────────────────────────────────────────────
    3)
        echo
        echo " Goodbye!"
        sleep 2
        exit 0
        ;;

    *)
        echo " Invalid option. Please enter 1, 2, or 3."
        sleep 2
        ;;

    esac
done
