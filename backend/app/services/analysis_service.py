"""
analysis_service.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provides:
  - Weighted linear regression (weighted by total_ms)
  - Weighted centroid calculation
  - Dominant quadrant detection
  - Gemini "music astrology" personality reading
"""

import os, re, json, logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("analysis_service")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-04-17")


# ── Linear Regression ─────────────────────────────────────────────────────────
def linear_regression(songs: list, x_axis: str = "energy", y_axis: str = "valence") -> dict:
    """
    Weighted linear regression: y = slope * x + intercept
    Weight = total_ms so heavily-played songs have more influence.
    Returns slope, intercept, r_squared, interpretation.
    """
    valid = [s for s in songs if s.get(x_axis) is not None and s.get(y_axis) is not None]
    n     = len(valid)
    if n < 3:
        return {"error": "Need at least 3 songs", "n": n}

    weights = [max(s.get("total_ms", 1), 1) for s in valid]
    total_w = sum(weights)
    xs = [s[x_axis] for s in valid]
    ys = [s[y_axis] for s in valid]

    x_mean = sum(w * x for w, x in zip(weights, xs)) / total_w
    y_mean = sum(w * y for w, y in zip(weights, ys)) / total_w

    num   = sum(w * (x - x_mean) * (y - y_mean) for w, x, y in zip(weights, xs, ys))
    denom = sum(w * (x - x_mean) ** 2            for w, x    in zip(weights, xs))

    slope     = (num / denom) if denom else 0.0
    intercept = y_mean - slope * x_mean

    ss_res = sum(w * (y - (slope * x + intercept)) ** 2 for w, x, y in zip(weights, xs, ys))
    ss_tot = sum(w * (y - y_mean) ** 2                   for w, y    in zip(weights, ys))
    r_sq   = 1.0 - (ss_res / ss_tot) if ss_tot else 0.0

    return {
        "slope":         round(slope,     4),
        "intercept":     round(intercept, 4),
        "r_squared":     round(r_sq,      4),
        "x_mean":        round(x_mean,    4),
        "y_mean":        round(y_mean,    4),
        "n_songs":       n,
        "x_axis":        x_axis,
        "y_axis":        y_axis,
        "interpretation": _interpret(slope, r_sq),
    }


def _interpret(slope: float, r_sq: float) -> str:
    consistency = (
        "very consistent pattern" if r_sq > 0.6 else
        "clear pattern"           if r_sq > 0.35 else
        "weak pattern"            if r_sq > 0.1  else
        "scattered — almost no pattern"
    )
    if slope > 0.3 and r_sq > 0.15:
        return f"You reach for upbeat, happy music when you want energy. Energy and happiness rise together ({consistency}, R²={r_sq:.2f})."
    if slope < -0.3 and r_sq > 0.15:
        return f"You reach for darker, more intense music when you need energy. Your hype songs have edge ({consistency}, R²={r_sq:.2f})."
    return f"Energy and mood are largely independent in your listening — a true omnivore ({consistency}, R²={r_sq:.2f})."


# ── Centroid ──────────────────────────────────────────────────────────────────
def calculate_centroid(songs: list) -> dict:
    """Weighted average of energy and valence, weighted by total_ms."""
    valid = [s for s in songs if s.get("energy") is not None and s.get("valence") is not None]
    if not valid:
        return {"energy": 0.5, "valence": 0.5}
    total_w = sum(max(s.get("total_ms", 1), 1) for s in valid)
    energy  = sum(max(s.get("total_ms", 1), 1) * s["energy"]  for s in valid) / total_w
    valence = sum(max(s.get("total_ms", 1), 1) * s["valence"] for s in valid) / total_w
    return {"energy": round(energy, 4), "valence": round(valence, 4)}


def dominant_quadrant(centroid: dict) -> str:
    e, v = centroid["energy"], centroid["valence"]
    if e >= 0.5 and v >= 0.5: return "Energetic & Happy"
    if e >= 0.5 and v <  0.5: return "Energetic & Dark"
    if e <  0.5 and v >= 0.5: return "Chill & Happy"
    return "Melancholic"


# ── Music Astrology ───────────────────────────────────────────────────────────
def generate_astrology(
    user_name: str,
    songs: list,
    centroid: dict,
    quadrant: str,
    regression: dict,
) -> dict:
    """Send listening data to Gemini Flash and get a music personality reading."""
    top = sorted(songs, key=lambda s: s.get("total_ms", 0), reverse=True)[:8]
    top_text = "\n".join(
        f'  "{s["track"]}" by {s["artist"]} ({s.get("total_ms", 0) // 60000} min)'
        for s in top
    )

    prompt = f"""You are a mystical music astrologer. Read this person's listening data like a cosmic chart.

Name: {user_name}
Centroid: energy={centroid['energy']}, valence={centroid['valence']}
Dominant quadrant: {quadrant}
Regression: slope={regression.get('slope','?')}, R²={regression.get('r_squared','?')}
Pattern: {regression.get('interpretation','?')}

Most played songs:
{top_text}

Write a vivid, data-grounded music astrology reading. Reference the actual numbers.
Be poetic but specific — never generic.

Return ONLY valid JSON (no markdown):
{{
  "archetype":  "<2-4 word cosmic archetype>",
  "headline":   "<one punchy sentence about their musical identity>",
  "reading":    "<3 sentences, vivid and data-specific>",
  "element":    "<Fire|Water|Earth|Air|Void|Plasma>",
  "hz":         "<plausible resonance frequency in Hz>"
}}"""

    if not GEMINI_API_KEY:
        return _fallback_reading(user_name, quadrant, centroid)

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction="You are a mystical music astrologer. Return only JSON."
        )
        raw  = model.generate_content(prompt).text.strip()
        raw  = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        log.error(f"Gemini astrology error: {e}")
        return _fallback_reading(user_name, quadrant, centroid)


def _fallback_reading(name: str, quadrant: str, centroid: dict) -> dict:
    archetypes = {
        "Energetic & Happy": "The Solar Celebrant",
        "Energetic & Dark":  "The Storm Wanderer",
        "Chill & Happy":     "The Warm Drifter",
        "Melancholic":       "The Midnight Archivist",
    }
    return {
        "archetype": archetypes.get(quadrant, "The Cosmic Listener"),
        "headline":  f"{name} orbits the {quadrant} quadrant of the musical universe.",
        "reading":   f"With energy at {centroid['energy']:.0%} and valence at {centroid['valence']:.0%}, your sonic gravity pulls toward {quadrant.lower()} soundscapes.",
        "element":   "Void",
        "hz":        "432 Hz",
    }
