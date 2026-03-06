import json
import os
import shutil

WATCHLISTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlists.json")


def _read_file() -> dict:
    if not os.path.exists(WATCHLISTS_FILE):
        return {}
    try:
        with open(WATCHLISTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_file(data: dict) -> None:
    tmp = WATCHLISTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    shutil.move(tmp, WATCHLISTS_FILE)


def load() -> list:
    return _read_file().get("panes", [])


def save(panes: list) -> None:
    data = _read_file()
    data["panes"] = panes
    _write_file(data)


def load_aliases() -> dict:
    return _read_file().get("aliases", {})


def save_aliases(aliases: dict) -> None:
    data = _read_file()
    data["aliases"] = aliases
    _write_file(data)
