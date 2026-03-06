import json
import os
import shutil

WATCHLISTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlists.json")


def load() -> list:
    if not os.path.exists(WATCHLISTS_FILE):
        return []
    try:
        with open(WATCHLISTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("panes", [])
    except (json.JSONDecodeError, OSError):
        return []


def save(panes: list) -> None:
    tmp = WATCHLISTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"panes": panes}, f, indent=2)
    shutil.move(tmp, WATCHLISTS_FILE)
