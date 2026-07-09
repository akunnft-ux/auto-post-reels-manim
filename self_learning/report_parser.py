import json
import os
import re
from datetime import datetime

try:
    from google import genai
except ImportError:
    genai = None


def parse_report(report_text: str) -> dict:
    """
    Uses Gemini to extract structured insights from a performance report.
    Returns:
    {
        "hook_performance": [
            {"hook_text": "...", "avg_views": 251, "post_count": 3}
        ],
        "posting_time_performance": [
            {"hour": 2, "avg_views": 269.5, "post_count": 2}
        ],
        "cta_analysis": {
            "current_cta_issue": "...",
            "recommended_cta": "..."
        },
        "content_type_recommendations": "...",
        "content_pillar_recommendations": "...",
        "summary_metrics": {
            "total_views": 10010,
            "avg_views_per_reel": 159,
            "total_comments": 0,
            "distribution_multiplier": -0.17
        }
    }
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or genai is None:
        print("[SL][REPORT] Gemini not available for report parsing")
        return {}

    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    prompt = (
        "You are an analytics data extractor. From the performance report below, extract structured data.\n"
        "Return valid JSON only, no markdown wrapping.\n\n"
        "Expected JSON schema:\n"
        "{\n"
        '  "hook_performance": [{"hook_text": "...", "avg_views": 251, "post_count": 3}],\n'
        '  "posting_time_performance": [{"hour": 2, "avg_views": 269.5, "post_count": 2}],\n'
        '  "cta_analysis": {"current_cta_issue": "...", "recommended_cta": "..."},\n'
        '  "content_type_recommendations": "...",\n'
        '  "content_pillar_recommendations": "...",\n'
        '  "summary_metrics": {"total_views": 10010, "avg_views_per_reel": 159, "total_comments": 0, "distribution_multiplier": -0.17}\n'
        "}\n\n"
        "If the report doesn't contain a field, leave it as null or empty.\n\n"
        f"Report:\n{report_text[:10000]}"
    )

    try:
        response = client.models.generate_content(model=model, contents=prompt)
        text = response.text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception as e:
        print(f"[SL][REPORT] Gemini parse failed: {e}")

    return {}
