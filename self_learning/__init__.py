import os
import json
import tempfile
from datetime import datetime

from .csv_parser import parse_csv
from .analytics_store import load_analytics_records, save_analytics_records, merge_records
from .analytics_store import load_classifications, save_classification
from .classifier import classify_records
from .learning_engine import compute_learning_config, load_learning_config, save_learning_config

ANALYTICS_PATH = "data/analytics_records.json"
CLASSIFICATION_PATH = "data/classification.json"
LEARNING_ITERATION_PATH = "data/learning_iteration.json"
LEARNING_CONFIG_PATH = "self_learning/learning_config.json"


def run_self_learning(csv_path: str) -> dict:
    """
    Orchestrate the full self-learning pipeline from a CSV file.
    Returns a summary dict.
    """
    result = {"status": "ok", "records_parsed": 0, "classifications": {}, "changes_made": []}

    # 1. Parse CSV
    records = parse_csv(csv_path)
    if not records:
        result["status"] = "skipped"
        result["reason"] = "no_records_parsed"
        return result
    result["records_parsed"] = len(records)

    # 2. Merge with existing
    existing = load_analytics_records(ANALYTICS_PATH)
    merged = merge_records(existing, records)
    save_analytics_records(ANALYTICS_PATH, merged)
    result["total_records"] = len(merged)

    # 3. Classify
    classifications = classify_records(merged)
    if not classifications:
        result["status"] = "skipped"
        result["reason"] = "insufficient_data_for_classification"
        return result

    existing_classifications = load_classifications(CLASSIFICATION_PATH)
    existing_classifications.extend(classifications)
    save_classification(CLASSIFICATION_PATH, existing_classifications)

    counts = {"viral": 0, "good": 0, "bad": 0}
    for c in classifications:
        counts[c["classification"]] = counts.get(c["classification"], 0) + 1
    result["classifications"] = counts

    # 4. Compute learning update
    current_config = load_learning_config(LEARNING_CONFIG_PATH)
    new_config, iteration = compute_learning_config(current_config, classifications, merged)

    if iteration:
        save_learning_config(LEARNING_CONFIG_PATH, new_config)

        iterations = _load_json(LEARNING_ITERATION_PATH, [])
        iterations.append(iteration)
        _save_json(LEARNING_ITERATION_PATH, iterations)

        result["changes_made"] = [iteration["variable_changed"]]
        result["variable_changed"] = iteration["variable_changed"]
        result["previous_value"] = iteration["previous_value"]
        result["new_value"] = iteration["new_value"]

    return result


def _load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
