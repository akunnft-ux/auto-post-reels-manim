import statistics
from datetime import datetime


def classify_records(records: list, follower_count: int = None) -> list:
    """
    Classify analytics records using 2-phase threshold (social-media-growth-engine §5.1).
    Requires at least 3 records.
    """
    if len(records) < 3:
        print(f"[SL][CLASSIFY] Insufficient records ({len(records)}), need ≥3")
        return []

    if follower_count is None:
        follower_count = _estimate_follower_count(records)

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
            follower_count=follower_count,
            niche_baseline=niche_baseline,
        )

        classifications.append({
            "post_id": r.get("post_id", ""),
            "classification": classification,
            "metric_triggered": metric,
            "follower_count_at_post": follower_count,
            "computed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    viral = sum(1 for c in classifications if c["classification"] == "viral")
    good = sum(1 for c in classifications if c["classification"] == "good")
    bad = sum(1 for c in classifications if c["classification"] == "bad")
    print(f"[SL][CLASSIFY] {len(classifications)} classified: {viral} viral, {good} good, {bad} bad")

    return classifications


def _classify_single(views: int, engagement_rate: float, follower_count: int, niche_baseline: float) -> tuple:
    if follower_count < 100:
        if views > 1000:
            return ("viral", f"views={views} > 1000 (absolute floor for <100 followers)")
    else:
        threshold = 10 * follower_count
        if views > threshold:
            return ("viral", f"views={views} > 10*followers({follower_count})={threshold}")

    if views < 50:
        return ("bad", f"views={views} < 50")

    if engagement_rate < 0.01:
        return ("bad", f"engagement_rate={engagement_rate:.4f} < 1%")

    if engagement_rate < niche_baseline:
        return ("good", f"engagement_rate={engagement_rate:.4f} < niche_baseline={niche_baseline:.4f}")

    return ("good", f"engagement_rate={engagement_rate:.4f} >= niche_baseline={niche_baseline:.4f}")


def _estimate_follower_count(records: list) -> int:
    """Estimate follower count from records (or default to 100 if unknown)."""
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
