import json
import os
from datetime import datetime


def load_analytics_records(path: str) -> list:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_analytics_records(path: str, records: list):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def merge_records(existing: list, new_records: list, max_records: int = 500) -> list:
    ids = {}
    for r in existing:
        pid = r.get("post_id", "")
        ids[pid] = r

    for r in new_records:
        pid = r.get("post_id", "")
        if pid:
            ids[pid] = r

    merged = list(ids.values())
    merged.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
    return merged[:max_records]


def load_classifications(path: str) -> list:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_classification(path: str, records: list, max_records: int = 500):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    records = records[-max_records:]
    with open(path, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
