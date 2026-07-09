import os
import json
import tempfile
from datetime import datetime
from copy import deepcopy

from .csv_parser import parse_csv
from .analytics_store import load_analytics_records, save_analytics_records, merge_records
from .analytics_store import load_classifications, save_classification
from .classifier import classify_records
from .learning_engine import compute_learning_config, load_learning_config, save_learning_config
from .learning_engine import _update_posting_schedule, _update_content_pillar
from .report_parser import parse_report

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


def run_self_learning_from_report(report_text: str) -> dict:
    """
    Ingest a structured performance report and update learning config.
    Returns a summary dict (same shape as run_self_learning).
    """
    result = {"status": "ok", "records_parsed": 0, "classifications": {}, "changes_made": []}

    insights = parse_report(report_text)
    if not insights:
        result["status"] = "skipped"
        result["reason"] = "no_insights_extracted"
        return result

    current_config = load_learning_config(LEARNING_CONFIG_PATH)
    new_config = deepcopy(current_config)
    iterations = []

    hook_perf = insights.get("hook_performance")
    if hook_perf:
        sorted_hooks = sorted(hook_perf, key=lambda h: h.get("avg_views", 0), reverse=True)
        if "hook_templates" in new_config:
            old_hooks = deepcopy(new_config["hook_templates"])
            for content_type in new_config["hook_templates"]:
                matched = [h["hook_text"] for h in sorted_hooks if h.get("hook_text")]
                if matched:
                    existing = new_config["hook_templates"].get(content_type, [])
                    reordered = [m for m in matched if m in existing]
                    reordered.extend([e for e in existing if e not in reordered])
                    new_config["hook_templates"][content_type] = reordered
            if old_hooks != new_config["hook_templates"]:
                iterations.append({
                    "id": f"iter-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-hook",
                    "variable_changed": "hook_templates",
                    "previous_value": old_hooks,
                    "new_value": deepcopy(new_config["hook_templates"]),
                    "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                })

    posting_time = insights.get("posting_time_performance")
    if posting_time:
        iteration = _update_posting_schedule(new_config, posting_time)
        if iteration:
            iterations.append(iteration)

    cta_analysis = insights.get("cta_analysis")
    if cta_analysis and cta_analysis.get("recommended_cta"):
        old_cta = deepcopy(new_config.get("cta_pool", []))
        rec_cta = cta_analysis["recommended_cta"]
        if rec_cta not in new_config.get("cta_pool", []):
            pool = new_config.get("cta_pool", [])
            new_config["cta_pool"] = [rec_cta] + pool
            iterations.append({
                "id": f"iter-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-cta",
                "variable_changed": "cta_pool",
                "previous_value": old_cta,
                "new_value": deepcopy(new_config["cta_pool"]),
                "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
        if cta_analysis.get("current_cta_issue"):
            new_config["cta_strategy"] = {
                "type": "comment_explicit" if "comment" in cta_analysis["recommended_cta"].lower() else "follow_generic",
                "explicit_cta": cta_analysis["recommended_cta"],
            }

    content_type_rec = insights.get("content_type_recommendations")
    if content_type_rec:
        old_weights = deepcopy(new_config.get("content_type_weights", {}))
        text_lower = content_type_rec.lower()
        if "stop photo" in text_lower:
            new_weights = {k: v for k, v in old_weights.items() if k in ("quiz", "fakta", "tips")}
            if new_weights and sum(new_weights.values()) > 0:
                total = sum(new_weights.values())
                for k in new_weights:
                    new_weights[k] = round(new_weights[k] / total, 2)
            if new_weights:
                new_config["content_type_weights"] = new_weights
                iterations.append({
                    "id": f"iter-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-ctype",
                    "variable_changed": "content_type_weights",
                    "previous_value": old_weights,
                    "new_value": deepcopy(new_weights),
                    "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                })

    pillar_rec = insights.get("content_pillar_recommendations")
    if pillar_rec:
        iteration = _update_content_pillar(new_config, pillar_rec)
        if iteration:
            iterations.append(iteration)

    summary = insights.get("summary_metrics", {})
    if summary and any(v is not None for v in summary.values()):
        new_config["report_data"] = {
            "total_views": summary.get("total_views"),
            "avg_views_per_reel": summary.get("avg_views_per_reel"),
            "total_comments": summary.get("total_comments"),
            "distribution_multiplier": summary.get("distribution_multiplier"),
            "report_source": f"report_ingested_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "report_ingested_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    if iterations:
        save_learning_config(LEARNING_CONFIG_PATH, new_config)

        all_iters = _load_json(LEARNING_ITERATION_PATH, [])
        all_iters.extend(iterations)
        _save_json(LEARNING_ITERATION_PATH, all_iters)

        result["changes_made"] = [it["variable_changed"] for it in iterations]
        result["iterations"] = len(iterations)
        result["insights_extracted"] = {k: bool(v) for k, v in insights.items() if v}
    else:
        result["status"] = "skipped"
        result["reason"] = "no_changes_from_report"

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
