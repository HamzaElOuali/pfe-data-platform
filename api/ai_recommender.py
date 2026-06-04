import json
import os
from typing import List

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/mistral-7b-instruct:free"
TIMEOUT = 8.0

FALLBACK = {
    "VIP": [
        "Standard fulfillment — no escalation required",
        "Consider cross-sell offer at delivery",
        "Customer shows loyalty signal — maintain engagement",
    ],
    "Loyal": [
        "Standard fulfillment — no escalation required",
        "Consider cross-sell offer at delivery",
        "Customer shows loyalty signal — maintain engagement",
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


async def get_ai_recommendations(scoring_result: dict) -> List[str]:
    """
    Call Mistral 7B via OpenRouter to generate 3 contextual recommendations.
    Falls back to static recommendations on any error.
    """
    segment = scoring_result.get("segment", "Loyal")
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key:
        return _fallback(segment)

    predicted_delay = scoring_result.get("predicted_delay_days", 0)
    risk_proba = scoring_result.get("risk_proba", 0)
    distance_km = scoring_result.get("distance_km", 0)
    total_price = scoring_result.get("total_items_price", 0)
    review_score = scoring_result.get("review_score", 3)
    order_month = scoring_result.get("order_month", 6)

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

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://pfe-data-platform.local",
                    "X-Title": "PFE Data Intelligence Platform",
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.4,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()

            # Strip markdown code fences if present
            if "```" in content:
                parts = content.split("```")
                content = parts[1] if len(parts) > 1 else parts[0]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            # Find first [ ... ] block in case model added preamble
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                content = content[start: end + 1]

            recs = json.loads(content)
            if isinstance(recs, list) and len(recs) >= 3:
                return [str(r) for r in recs[:3]]
            return _fallback(segment)

    except Exception:
        return _fallback(segment)
