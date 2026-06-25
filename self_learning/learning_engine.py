import json
import os
from datetime import datetime
from copy import deepcopy

LEARNING_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "learning_config.json")

VARIABLE_ORDER = ["content_type_weights", "hook_ranking", "cta_ranking", "hashtag_ranking"]

DEFAULT_CONFIG = {
    "content_type_weights": {"quiz": 0.4, "fakta": 0.3, "tips": 0.3},
    "hook_templates": {},
    "cta_pool": [],
    "hashtag_pool": [],
    "variable_rotation_index": 0,
    "updated_at": None,
}


def load_learning_config(path: str = None) -> dict:
    if path is None:
        path = LEARNING_CONFIG_PATH
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cfg = deepcopy(DEFAULT_CONFIG)
        save_learning_config(path, cfg)
        return cfg


def save_learning_config(path: str, config: dict):
    config["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def compute_learning_config(current_config: dict, classifications: list, analytics_records: list) -> tuple:
    """
    Compute the next learning iteration.
    Returns (new_config, iteration_record) where iteration_record is None if no change.
    """
    if len(classifications) < 3:
        print(f"[SL][LEARN] Only {len(classifications)} classifications, need ≥3 to learn")
        return current_config, None

    config = deepcopy(current_config)
    rotation_index = config.get("variable_rotation_index", 0)
    variable = VARIABLE_ORDER[rotation_index % len(VARIABLE_ORDER)]

    viral_ids = {c["post_id"] for c in classifications if c["classification"] == "viral"}
    good_ids = {c["post_id"] for c in classifications if c["classification"] == "good"}
    bad_ids = {c["post_id"] for c in classifications if c["classification"] == "bad"}

    if not viral_ids and not good_ids:
        print("[SL][LEARN] No viral or good posts to learn from")
        return current_config, None

    iteration = None

    if variable == "content_type_weights":
        iteration = _adjust_weights(config, classifications, analytics_records)
    elif variable == "hook_ranking":
        iteration = _rank_templates(config, analytics_records, viral_ids, "hook_templates")
    elif variable == "cta_ranking":
        iteration = _rank_templates(config, analytics_records, viral_ids, "cta_pool")
    elif variable == "hashtag_ranking":
        iteration = _rank_hashtags(config, analytics_records, viral_ids)

    if iteration:
        config["variable_rotation_index"] = (rotation_index + 1) % len(VARIABLE_ORDER)

    return config, iteration


def _adjust_weights(config: dict, classifications: list, analytics_records: list) -> dict:
    """Adjust content_type_weights based on viral/good ratio per type."""
    post_type_map = {}
    for r in analytics_records:
        post_type_map[r.get("post_id", "")] = r.get("content_type", "quiz")

    type_stats = {}
    for c in classifications:
        pid = c["post_id"]
        ctype = post_type_map.get(pid, "quiz")
        if ctype not in type_stats:
            type_stats[ctype] = {"viral": 0, "good": 0, "bad": 0, "total": 0}
        cls = c["classification"]
        type_stats[ctype][cls] = type_stats[ctype].get(cls, 0) + 1
        type_stats[ctype]["total"] += 1

    if not type_stats:
        return None

    old_weights = deepcopy(config.get("content_type_weights", {}))
    new_weights = {}

    total_viral_good = sum(s["viral"] + s["good"] for s in type_stats.values())
    if total_viral_good == 0:
        return None

    for ctype, stats in type_stats.items():
        vg_ratio = (stats["viral"] + stats["good"]) / max(stats["total"], 1)
        new_weights[ctype] = vg_ratio

    if not new_weights:
        return None

    total = sum(new_weights.values())
    if total > 0:
        for k in new_weights:
            new_weights[k] = round(max(0.1, min(0.7, new_weights[k] / total)), 2)

    total = sum(new_weights.values())
    if abs(total - 1.0) > 0.01:
        diff = round(1.0 - total, 2)
        max_key = max(new_weights, key=new_weights.get)
        new_weights[max_key] = round(new_weights[max_key] + diff, 2)

    config["content_type_weights"] = new_weights

    return {
        "id": f"iter-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "variable_changed": "content_type_weights",
        "previous_value": old_weights,
        "new_value": deepcopy(new_weights),
        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _rank_templates(config: dict, analytics_records: list, viral_ids: set, pool_key: str) -> dict:
    """Re-rank hook/CTA templates by engagement rate."""
    if pool_key not in config or not config[pool_key]:
        return None

    old_value = deepcopy(config[pool_key])

    pool = config[pool_key]

    if isinstance(pool, dict):
        ranked = {}
        for ctype, templates in pool.items():
            scored = []
            for t in templates:
                score = _compute_template_score(t, analytics_records, viral_ids)
                scored.append((score, t))
            scored.sort(key=lambda x: x[0], reverse=True)
            ranked[ctype] = [t for _, t in scored]
        config[pool_key] = ranked
    elif isinstance(pool, list):
        scored = []
        for t in pool:
            score = _compute_template_score(t, analytics_records, viral_ids)
            scored.append((score, t))
        scored.sort(key=lambda x: x[0], reverse=True)
        config[pool_key] = [t for _, t in scored]
    else:
        return None

    return {
        "id": f"iter-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "variable_changed": pool_key,
        "previous_value": old_value,
        "new_value": deepcopy(config[pool_key]),
        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _rank_hashtags(config: dict, analytics_records: list, viral_ids: set) -> dict:
    """Re-rank hashtag pool by frequency in viral posts."""
    pool_key = "hashtag_pool"
    if pool_key not in config or not config[pool_key]:
        return None

    old_value = deepcopy(config[pool_key])
    pool = config[pool_key]

    scored = []
    for tag in pool:
        count = sum(1 for pid in viral_ids for r in analytics_records if r.get("post_id") == pid and tag in str(r))
        scored.append((count, tag))

    scored.sort(key=lambda x: x[0], reverse=True)
    config[pool_key] = [t for _, t in scored]

    return {
        "id": f"iter-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "variable_changed": pool_key,
        "previous_value": old_value,
        "new_value": deepcopy(config[pool_key]),
        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _compute_template_score(template: str, analytics_records: list, viral_ids: set) -> float:
    """Score a template by how often it appears in viral posts."""
    viral_count = sum(1 for pid in viral_ids for r in analytics_records if r.get("post_id") == pid)
    return viral_count
