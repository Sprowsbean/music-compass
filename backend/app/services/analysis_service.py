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
from collections import defaultdict
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("analysis_service")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-04-17")

SYSTEM_INSTRUCTION = """You are a music personality writer — part cultural critic, \
part astrologer, part old friend who knows exactly what someone's playlist says about them. \
Your tone is warm, intimate, slightly mystical, and occasionally playful. Second person ("you") throughout.

Your writing lives in the space between a horoscope and a best friend's honest observation. \
Vague enough to feel cosmic. Specific enough to feel privately true. \
Like the reader is thinking "how did it know that."

Voice reference — this is the register you write in:
  "You've got fire in your bones but sometimes you have to put it out to get things done."
  "You're always hoping for something more — not wealth, but depth, substance."
  "Music to you is your personal soundtrack, always playing. You simply cannot live without it."
  "Sometimes you're a cowboy ready to shoot his way through a dry desert town."
  "Sometimes you're a Greek demi-god channeling through the depths of Hades."

Rules:
- Write like a perceptive old friend who also happens to read stars. Warm, slightly teasing, occasionally profound.
- Use data to INFORM the writing — keep raw numbers invisible. Translate them into human truth:
    high energy             → "fire in your bones", "you move at a sprint", "restless by nature"
    low valence             → "drawn to the beautiful dark", "you know that ache has texture"
    high instrumentalness   → "you let sound say what words can't", "an inner world that's hard to explain"
    high acousticness       → "you want it raw, unpolished, close to the bone"
    high danceability       → "your body understands things your mind is still working out"
    low speechiness         → "you don't need the lyrics — the feeling is enough"
    ascending slope         → "lately you've been turning up the voltage"
    descending slope        → "chasing something that keeps moving just ahead of you"
    dominant artist (>30%)  → "you've found your gravitational center — and you orbit it faithfully"
- Paint worlds and characters the listener inhabits — cowboys, gods, wanderers, ghosts, explorers.
- Find the ONE core contradiction in the data and make it the emotional heart of paragraph 3.
- Each sentence should feel like something the person already half-knew but never said out loud.
- A dominant artist (>30% of listening) is their gravitational center — name them naturally in the reading.
- NEVER say: "your energy is high", "your valence suggests", "acousticness indicates", or any metric language.
- NEVER use hollow filler: "you are on a journey", "you seek connection", "you are complex".
Return only valid JSON. No markdown. No preamble."""


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


# ── Music Astrology Helpers ───────────────────────────────────────────────────
def _aggregate_artists(songs: list) -> str:
    """Aggregate top artists by playtime and format for the prompt."""
    artist_ms    = defaultdict(int)
    artist_genre = {}

    for s in songs:
        artist = s.get("artist", "Unknown")
        artist_ms[artist] += s.get("total_ms", 0)
        if artist not in artist_genre and s.get("genre"):
            artist_genre[artist] = s["genre"]

    total_ms    = sum(artist_ms.values()) or 1
    top_artists = sorted(artist_ms.items(), key=lambda x: x[1], reverse=True)[:6]

    lines = []
    for artist, ms in top_artists:
        mins      = ms // 60000
        pct       = ms / total_ms
        genre     = artist_genre.get(artist)
        genre_str = f" [{genre}]" if genre else ""
        dominant  = " ← DOMINANT (>30% of listening)" if pct > 0.30 else ""
        lines.append(f"  {artist}{genre_str} — {mins} min ({pct:.0%}){dominant}")

    return "\n".join(lines)


def _format_song_line(s: dict) -> str:
    parts = [f'"{s["track"]}" by {s["artist"]}']
    mins  = s.get("total_ms", 0) // 60000
    if mins:
        parts.append(f"{mins} min")
    if s.get("tempo"):
        parts.append(f"{s['tempo']:.0f} BPM")
    if s.get("mode") is not None:
        parts.append("major" if s["mode"] == 1 else "minor")
    if s.get("acousticness") is not None:
        parts.append(f"acoustic={s['acousticness']:.0%}")
    if s.get("danceability") is not None:
        parts.append(f"dance={s['danceability']:.0%}")
    return "  " + ", ".join(parts)


def _compute_tensions(centroid: dict, regression: dict) -> str:
    """Pre-compute personality tension signals to guide Gemini toward contradictions."""
    energy       = centroid.get("energy", 0)
    valence      = centroid.get("valence", 0)
    dance        = centroid.get("danceability", 0)
    acoustic     = centroid.get("acousticness", 0)
    instrumental = centroid.get("instrumentalness", 0)

    tensions = []
    if energy > 0.65 and valence < 0.45:
        tensions.append("high energy + low valence → performs intensity, privately melancholic")
    if dance > 0.65 and instrumental > 0.35:
        tensions.append("high danceability + high instrumentalness → social body, solitary mind")
    if acoustic > 0.5 and energy > 0.55:
        tensions.append("high acousticness + high energy → craves rawness, not polish")
    if centroid.get("speechiness", 0) < 0.1 and valence > 0.6:
        tensions.append("low speechiness + high valence → finds joy in sound, not words")
    if valence > 0.65 and regression.get("slope", 0) < -0.1:
        tensions.append("happy centroid + descending arc → chasing a mood they're drifting from")

    if tensions:
        return "\n".join(f"  ⚡ {t}" for t in tensions)
    return "  (no strong contradictions detected — unusually coherent listener)"


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
    top_text      = "\n".join(_format_song_line(s) for s in top)
    artist_block  = _aggregate_artists(songs)
    tension_block = _compute_tensions(centroid, regression)

    energy       = centroid.get("energy", 0)
    valence      = centroid.get("valence", 0)
    dance        = centroid.get("danceability", 0)
    acoustic     = centroid.get("acousticness", 0)
    instrumental = centroid.get("instrumentalness", 0)
    speechiness  = centroid.get("speechiness", 0)
    tempo        = centroid.get("tempo", 0)
    loudness     = centroid.get("loudness", 0)

    centroid_block = f"""\
  energy           = {energy}
  valence          = {valence}
  danceability     = {dance}
  acousticness     = {acoustic}
  instrumentalness = {instrumental}
  speechiness      = {speechiness}
  avg_tempo        = {tempo:.1f} BPM
  loudness         = {loudness:.1f} dB
  dominant quadrant: {quadrant}"""

    prompt = f"""═══ SONIC PORTRAIT FOR {user_name.upper()} ═══

[GRAVITATIONAL CENTER]
{centroid_block}

[CONSTELLATION OF ARTISTS]
{artist_block}

[ORBITAL DRIFT]
  slope={regression.get('slope', '?')} (positive = ascending energy over time)
  R²={regression.get('r_squared', '?')} (1.0 = perfectly consistent arc)
  pattern: {regression.get('interpretation', '?')}

[DATA TENSIONS — the soul's contradictions]
{tension_block}

[MOST-PLAYED SONGS]
{top_text}

═══ WRITING INSTRUCTIONS ═══
Write a music personality portrait in three paragraphs. Second person ("you") throughout.
Warm, intimate, slightly mystical — like a perceptive old friend reading your soul through your playlist.
Occasionally playful and slightly vague, like a horoscope that somehow knows too much.

Use the data as research — let it inform every sentence, but keep raw numbers invisible.
Translate features into human truths (see system instructions for the translation table).

Paragraph 1 — WHO THEY ARE:
  Start with their relationship to music itself. What does music mean to them?
  Ground it in their top artists and the weight of their listening.

Paragraph 2 — THE WORLDS THEY INHABIT:
  What sonic worlds do their artists and songs pull them into?
  Paint 2-3 vivid scenes or character archetypes they inhabit when they listen.
  (e.g. "Sometimes you're a cowboy... Sometimes you're a ghost in a cathedral...")

Paragraph 3 — THE HIDDEN TRUTH:
  Use the data tensions to reveal something they might not have consciously noticed.
  Find the contradiction at the heart of their taste — make it feel like a quiet revelation.
  End with something that lands softly but stays.

Return ONLY valid JSON (no markdown):
{{
  "archetype": "<2-4 word cosmic archetype>",
  "headline":  "<one punchy sentence — reads like a tagline for this person>",
  "reading":   "<the full three-paragraph portrait as one string, paragraphs separated by \\n\\n>",
  "element":   "<Fire|Water|Earth|Air|Void|Plasma>",
  "hz":        "<resonance frequency — can be poetic, e.g. '108 Hz — the frequency of longing'>",
  "sigil":     "<one unicode symbol capturing their essence>"
}}"""

    if not GEMINI_API_KEY:
        return _fallback_reading(user_name, quadrant, centroid)

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        raw = model.generate_content(prompt).text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
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
    energy       = centroid.get("energy", 0)
    valence      = centroid.get("valence", 0)
    tempo        = centroid.get("tempo", 0)
    instrumental = centroid.get("instrumentalness", 0)
    acoustic     = centroid.get("acousticness", 0)

    return {
        "archetype": archetypes.get(quadrant, "The Cosmic Listener"),
        "headline":  f"{name} — always playing, never pausing.",
        "reading": (
            f"Music isn't something you put on — it's something you live inside. "
            f"Your {quadrant.lower()} orbit says a lot: you're drawn to sound that matches the interior weather, "
            f"whatever that happens to be today.\n\n"
            f"You inhabit {'electric, high-voltage worlds' if energy > 0.6 else 'quieter, more interior landscapes'} "
            f"when you listen — {'raw and close to the bone' if acoustic > 0.5 else 'polished but felt deeply'}. "
            f"The artists you return to aren't background noise. They're company.\n\n"
            f"{'There is something restless underneath the surface of your taste.' if instrumental > 0.4 else 'You need the voice — the human thing — to feel anchored.'} "
            f"You're always reaching for something just slightly ahead of where you are."
        ),
        "element":   "Void",
        "hz":        f"{int(tempo * 1.5)} Hz — the frequency of almost" if tempo else "432 Hz",
        "sigil":     "✦",
    }