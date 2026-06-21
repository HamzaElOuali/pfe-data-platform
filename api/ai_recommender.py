import asyncio
import json
import os
from typing import List, Tuple

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_MODEL_TIMEOUT = httpx.Timeout(connect=4.0, read=10.0, write=4.0, pool=4.0)
_GLOBAL_TIMEOUT = 22.0

MODELS = [
    "openrouter/free",                              # meta-router — always has capacity
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]

FALLBACK = {
    "VIP": [
        "Apply priority SLA — escalate to VIP courier tier",
        "Trigger exclusive loyalty reward at delivery",
        "Cross-sell premium offer — high lifetime value customer",
    ],
    "Loyal": [
        "Standard fulfillment — maintain current service level",
        "Enroll customer in loyalty reward program",
        "Propose mid-tier cross-sell — consistent buying pattern",
    ],
    "At Risk": [
        "Escalate to logistics — immediate SLA review required",
        "Send proactive notification with compensation voucher",
        "Trigger retention campaign — churn signal detected",
    ],
    "Lost": [
        "Flag order for priority review",
        "Escalate customer to retention team",
        "Offer recovery incentive before delivery",
    ],
}


def _fallback(segment: str) -> List[str]:
    return FALLBACK.get(segment, FALLBACK["Loyal"])


def _parse_recs(content: str) -> List[str] | None:
    if "```" in content:
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    start, end = content.find("["), content.rfind("]")
    if start != -1 and end != -1:
        content = content[start: end + 1]
    try:
        recs = json.loads(content)
        if isinstance(recs, list) and len(recs) >= 3:
            return [str(r) for r in recs[:3]]
    except (json.JSONDecodeError, ValueError):
        pass
    return None


async def _try_models(prompt: str, headers: dict) -> List[str] | None:
    async with httpx.AsyncClient(timeout=_MODEL_TIMEOUT) as client:
        for model in MODELS:
            try:
                response = await client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 150,
                        "temperature": 0.4,
                    },
                )
                if response.status_code == 429:
                    continue
                if response.status_code != 200:
                    continue
                content = response.json()["choices"][0]["message"]["content"].strip()
                recs = _parse_recs(content)
                if recs:
                    return recs
            except Exception:
                continue
    return None


async def get_ai_recommendations(scoring_result: dict) -> Tuple[List[str], str]:
    """
    Returns (recommendations, source) where source is "ai" or "fallback".
    The caller can use source to decide whether to show the AI badge.
    """
    segment = scoring_result.get("segment", "Loyal")
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key:
        return _fallback(segment), "fallback"

    predicted_delay = scoring_result.get("predicted_delay_days", 0)
    risk_proba      = scoring_result.get("risk_proba", 0)
    distance_km     = scoring_result.get("distance_km", 0)
    total_price     = scoring_result.get("total_items_price", 0)
    review_score    = scoring_result.get("review_score", 3)
    order_month     = scoring_result.get("order_month", 6)

    prompt = f"""You are an e-commerce operations expert. Analyze this order scoring result and generate exactly 3 short actionable recommendations.

Order context:
- Predicted delivery delay: {predicted_delay:.1f} days
- Risk score: {risk_proba*100:.0f}%
- Customer segment: {segment}
- Distance: {distance_km} km
- Total price: {total_price} BRL
- Review score: {review_score}/5
- Order month: {order_month}

Rules:
- Each recommendation must be under 12 words
- Be specific to the context above
- Respond ONLY with a valid JSON array, no explanation, no markdown:
["recommendation 1", "recommendation 2", "recommendation 3"]
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pfe-data-platform.local",
        "X-Title": "PFE Data Intelligence Platform",
    }

    try:
        recs = await asyncio.wait_for(
            _try_models(prompt, headers),
            timeout=_GLOBAL_TIMEOUT,
        )
        if recs:
            return recs, "ai"
        return _fallback(segment), "fallback"
    except (asyncio.TimeoutError, Exception):
        return _fallback(segment), "fallback"
