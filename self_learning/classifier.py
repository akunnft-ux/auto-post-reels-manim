import json
import os
import statistics
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None


MIN_SAMPLE_THRESHOLD = 8


def classify_records(records: list, follower_count: int | None = None) -> list:
    """
    Classify analytics records using 2-phase threshold (social-media-growth-engine §5.1).
    Requires at least MIN_SAMPLE_THRESHOLD records.
    """
    if len(records) < MIN_SAMPLE_THRESHOLD:
        print(f"[SL][CLASSIFY] Insufficient records ({len(records)}), need ≥{MIN_SAMPLE_THRESHOLD}")
        return []

    if follower_count is None:
        follower_count = _estimate_follower_count()

    niche_baseline = _compute_niche_baseline(records)

    classifications = []
    for r in records:
        views = r.get("views", 0) or 0
        likes = r.get("likes", 0) or 0
        comments = r.get("comments", 0) or 0
        shares = r.get("shares", 0) or 0
        engagement_rate = r.get("engagement_rate", 0) or 0
        if engagement_rate == 0 and views > 0:
            engagement_rate = (likes + comments + shares) / views

        classification, metric = _classify_single(
            views=views,
            engagement_rate=engagement_rate,
            follower_count=follower_count or 0,
            niche_baseline=niche_baseline,
        )

        classifications.append({
            "post_id": r.get("post_id", ""),
            "classification": classification,
            "metric_triggered": metric,
            "follower_count_at_post": follower_count,
            "account_type": r.get("account_type"),
            "format": r.get("format"),
            "theme": r.get("theme"),
            "computed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    viral = sum(1 for c in classifications if c["classification"] == "viral")
    good = sum(1 for c in classifications if c["classification"] == "good")
    bad = sum(1 for c in classifications if c["classification"] == "bad")
    print(f"[SL][CLASSIFY] {len(classifications)} classified: {viral} viral, {good} good, {bad} bad")

    return classifications


def classify_records_by_combo(records: list, follower_count: int = None) -> dict:
    """
    Group records by (account_type, format, theme) combo and classify each group.
    Returns {combo_key: classifications_list}.
    Only includes combos with >= MIN_SAMPLE_THRESHOLD records.
    """
    if follower_count is None:
        follower_count = _estimate_follower_count()

    groups = {}
    for r in records:
        key = (r.get("account_type") or "unknown", r.get("format") or "unknown", r.get("theme") or "unknown")
        groups.setdefault(key, []).append(r)

    result = {}
    for key, group in groups.items():
        if len(group) < MIN_SAMPLE_THRESHOLD:
            print(f"[SL][CLASSIFY] Combo {key}: only {len(group)} records, need ≥{MIN_SAMPLE_THRESHOLD}, skipping")
            continue
        niche_baseline = _compute_niche_baseline(group)
        classifications = []
        for r in group:
            views = r.get("views", 0) or 0
            likes = r.get("likes", 0) or 0
            comments = r.get("comments", 0) or 0
            shares = r.get("shares", 0) or 0
            engagement_rate = r.get("engagement_rate", 0) or 0
            if engagement_rate == 0 and views > 0:
                engagement_rate = (likes + comments + shares) / views
            cls, met = _classify_single(views, engagement_rate, follower_count or 0, niche_baseline)
            classifications.append({
                "post_id": r.get("post_id", ""),
                "classification": cls,
                "metric_triggered": met,
                "follower_count_at_post": follower_count,
                "account_type": r.get("account_type"),
                "format": r.get("format"),
                "theme": r.get("theme"),
                "computed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
        result["/".join(key)] = classifications
        viral = sum(1 for c in classifications if c["classification"] == "viral")
        good = sum(1 for c in classifications if c["classification"] == "good")
        bad = sum(1 for c in classifications if c["classification"] == "bad")
        print(f"[SL][CLASSIFY] Combo {'/'.join(key)}: {len(classifications)} classified — {viral} viral, {good} good, {bad} bad")

    return result


def _classify_single(views: int, engagement_rate: float, follower_count: int, niche_baseline: float) -> tuple:
    fc = follower_count or 100
    if fc < 100:
        if views > 1000:
            return ("viral", f"views={views} > 1000 (absolute floor for <100 followers)")
    else:
        threshold = 10 * fc
        if views > threshold:
            return ("viral", f"views={views} > 10*followers({follower_count})={threshold}")

    if views < 50:
        return ("bad", f"views={views} < 50")

    if engagement_rate < 0.01:
        return ("bad", f"engagement_rate={engagement_rate:.4f} < 1%")

    if engagement_rate < niche_baseline:
        return ("good", f"engagement_rate={engagement_rate:.4f} < niche_baseline={niche_baseline:.4f}")

    return ("good", f"engagement_rate={engagement_rate:.4f} >= niche_baseline={niche_baseline:.4f}")


def _estimate_follower_count() -> int:
    """Fetch real follower count from Facebook API, growth.json, or default to 100."""
    # Try Facebook API
    fb_token = os.environ.get("FB_ACCESS_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    if fb_token and fb_page_id and requests is not None:
        try:
            resp = requests.get(
                f"https://graph.facebook.com/v25.0/{fb_page_id}",
                params={"access_token": fb_token, "fields": "followers_count"},
                timeout=10,
            )
            if resp.status_code == 200:
                count = resp.json().get("followers_count")
                if count is not None:
                    print(f"[SL][CLASSIFY] Fetched follower count from FB API: {count}")
                    return int(count)
        except Exception as e:
            print(f"[SL][CLASSIFY] FB API fetch failed: {e}")

    # Fallback: growth.json
    growth_path = os.path.join(os.path.dirname(__file__), "..", "data", "growth.json")
    try:
        with open(growth_path) as f:
            growth = json.load(f)
        if isinstance(growth, list) and growth:
            count = growth[-1].get("follower_count")
            if count is not None:
                print(f"[SL][CLASSIFY] Fetched follower count from growth.json: {count}")
                return int(count)
        elif isinstance(growth, dict):
            count = growth.get("follower_count")
            if count is not None:
                print(f"[SL][CLASSIFY] Fetched follower count from growth.json: {count}")
                return int(count)
    except (FileNotFoundError, json.JSONDecodeError, IndexError):
        pass

    return 100


def _compute_niche_baseline(records: list) -> float:
    """Compute trailing 30-day median engagement rate."""
    rates = []
    for r in records:
        views = r.get("views", 0) or 0
        likes = r.get("likes", 0) or 0
        comments = r.get("comments", 0) or 0
        shares = r.get("shares", 0) or 0
        if views > 0:
            rate = (likes + comments + shares) / views
            rates.append(rate)

    if len(rates) >= 3:
        return statistics.median(rates)

    return 0.05
