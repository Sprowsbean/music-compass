"""
kaggle_lookup.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Song Feature Lookup Engine

Lookup priority per song:
  1. Persistent JSON cache         (free, instant)
  2. Kaggle exact match            (O(1) HashMap on normalized track_name)
  3. Kaggle fuzzy match            (RapidFuzz ≥ 80 score)
  4. Gemini AI prediction          (calibrated with genre-matched examples)
  5. Neutral fallback 0.5/0.5

Kaggle CSV columns used:
  track_name, artists, energy, valence, track_genre
"""

import os, re, json, time, logging, unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger("kaggle_lookup")

# ── Config ────────────────────────────────────────────────────────────────────
KAGGLE_CSV_PATH = Path(os.getenv("KAGGLE_CSV_PATH", "data/kaggle/dataset.csv"))
CACHE_PATH      = Path(os.getenv("CACHE_PATH",      "backend/data/cache/score_cache.json"))
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

FUZZY_THRESHOLD = 80

SOURCE_EXACT   = "kaggle_exact"
SOURCE_FUZZY   = "kaggle_fuzzy"
SOURCE_GEMINI  = "gemini_predicted"
SOURCE_DEFAULT = "default"


# ── Normalizer ────────────────────────────────────────────────────────────────
def normalize(text: str) -> str:
    """
    Lowercase, strip accents, remove feat./bracket content, collapse spaces.
    Works correctly for CJK and accented characters.
    """
    if not text:
        return ""
    # Strip accents
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    # Remove featuring clauses
    text = re.sub(r"\s*(feat\.?|ft\.?|featuring|with)\s+.*", "", text)
    # Remove parenthetical / bracket content
    text = re.sub(r"[\(\[\{].*?[\)\]\}]", "", text)
    # Remove punctuation (keep letters, digits, spaces)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


# ── Cache ─────────────────────────────────────────────────────────────────────
class ScoreCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            log.info(f"Cache: {len(self._data)} entries loaded")

    def get(self, key: str) -> Optional[dict]:
        return self._data.get(key)

    def set(self, key: str, entry: dict):
        self._data[key] = {**entry, "cached_at": time.time()}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def stats(self) -> dict:
        by_source: dict = {}
        for e in self._data.values():
            s = e.get("source", "unknown")
            by_source[s] = by_source.get(s, 0) + 1
        return {"total": len(self._data), "by_source": by_source}


# ── Kaggle Index ──────────────────────────────────────────────────────────────
class KaggleIndex:
    """
    Builds two structures from dataset.csv:
      exact_map:    normalized_track_name → {energy, valence, genre, artists}
      genre_pools:  genre → list of {track, artist, energy, valence}  (for Gemini examples)
      artist_genre: normalized_artist → genre  (for genre detection)
    """

    def __init__(self, csv_path: Path):
        self.exact_map:    dict = {}
        self.genre_pools:  dict = {}
        self.artist_genre: dict = {}
        self.all_keys:     list = []
        self._build(csv_path)

    def _build(self, csv_path: Path):
        if not csv_path.exists():
            raise FileNotFoundError(
                f"Kaggle CSV not found at: {csv_path}\n"
                f"Download dataset.csv and place it at {csv_path}"
            )
        log.info(f"Building Kaggle index from {csv_path} …")
        df = pd.read_csv(csv_path, low_memory=False)

        built = 0
        for _, row in df.iterrows():
            raw_track  = str(row.get("track_name", "") or "").strip()
            raw_artist = str(row.get("artists",    "") or "").strip()
            genre      = str(row.get("track_genre","unknown") or "unknown").strip()

            if not raw_track:
                continue
            try:
                energy  = round(float(row["energy"]),  4)
                valence = round(float(row["valence"]), 4)
            except (ValueError, TypeError):
                continue

            norm = normalize(raw_track)
            if not norm:
                continue

            # First occurrence wins (dataset has duplicates across genres)
            if norm not in self.exact_map:
                self.exact_map[norm] = {
                    "energy":  energy,
                    "valence": valence,
                    "genre":   genre,
                    "_track":  raw_track,
                    "_artist": raw_artist,
                }
                self.all_keys.append(norm)
                built += 1

            # Genre pools (for Gemini calibration, capped at 200 per genre)
            pool = self.genre_pools.setdefault(genre, [])
            if len(pool) < 200:
                pool.append({
                    "track":   raw_track,
                    "artist":  raw_artist.split(";")[0],
                    "energy":  energy,
                    "valence": valence,
                })

            # Artist → genre mapping
            primary = normalize(raw_artist.split(";")[0])
            if primary and primary not in self.artist_genre:
                self.artist_genre[primary] = genre

        log.info(f"Kaggle index: {built} tracks, {len(self.genre_pools)} genres")

    def exact_lookup(self, norm: str) -> Optional[dict]:
        return self.exact_map.get(norm)

    def fuzzy_lookup(self, norm: str, threshold: int = FUZZY_THRESHOLD) -> Optional[tuple]:
        """Returns (entry, score, matched_key) or None."""
        try:
            from rapidfuzz import process, fuzz
            result = process.extractOne(
                norm, self.all_keys,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=threshold,
            )
            if result:
                matched_key, score, _ = result
                return self.exact_map[matched_key], int(score), matched_key
        except ImportError:
            # Fallback: simple substring check
            for key in self.all_keys:
                if norm in key or key in norm:
                    return self.exact_map[key], 75, key
        return None

    def detect_genre(self, artist: str) -> str:
        norm = normalize(artist.split(";")[0])
        return self.artist_genre.get(norm, "pop")

    def calibration_examples(self, genre: str, n: int = 10) -> list:
        import random
        pool = self.genre_pools.get(genre) or []
        if not pool:
            pool = [s for p in self.genre_pools.values() for s in p]
        return random.sample(pool, min(n, len(pool)))


# ── Gemini Predictor ──────────────────────────────────────────────────────────
class GeminiPredictor:
    SYSTEM = (
        "You are a music audio feature analyst. "
        "Predict Spotify-style energy and valence scores (0.0–1.0) for songs. "
        "Use the calibration examples to match the scale exactly. "
        "Respond with ONLY valid JSON — no markdown, no explanation."
    )

    def __init__(self):
        self._model = None

    def _model_(self):
        if not self._model:
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not set in .env")
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self._model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=self.SYSTEM,
            )
        return self._model

    def predict(self, track: str, artist: str, examples: list) -> Optional[dict]:
        ex_text = "\n".join(
            f'  "{e["track"]}" by {e["artist"]} → energy={e["energy"]}, valence={e["valence"]}'
            for e in examples
        )
        prompt = (
            f"Calibration examples from Spotify's audio features dataset:\n{ex_text}\n\n"
            f'Predict energy and valence for:\n  Track:  "{track}"\n  Artist: "{artist}"\n\n'
            f'Return ONLY JSON: {{"energy": <0.0-1.0>, "valence": <0.0-1.0>}}'
        )
        try:
            resp = self._model_().generate_content(prompt)
            raw  = re.sub(r"```json|```", "", resp.text).strip()
            data = json.loads(raw)
            return {
                "energy":  max(0.0, min(1.0, float(data["energy"]))),
                "valence": max(0.0, min(1.0, float(data["valence"]))),
            }
        except Exception as e:
            log.error(f"Gemini error for '{track}': {e}")
            return None


# ── Main Lookup Engine ────────────────────────────────────────────────────────
class SongLookupEngine:
    """
    Full 5-step pipeline:
      cache → kaggle exact → kaggle fuzzy → gemini → default

    Usage:
        engine = SongLookupEngine()
        result = engine.lookup("Fast Car", "Luke Combs", total_ms=1_000_000)
        # → { track, artist, total_ms, energy, valence, source, genre }
    """

    def __init__(self):
        self.cache  = ScoreCache(CACHE_PATH)
        self.kaggle = KaggleIndex(KAGGLE_CSV_PATH)
        self.gemini = GeminiPredictor()
        log.info("SongLookupEngine ready")

    def lookup(self, track: str, artist: str, total_ms: int = 0) -> dict:
        norm      = normalize(track)
        cache_key = f"{norm}|||{normalize(artist)}"

        # 1. Cache
        cached = self.cache.get(cache_key)
        if cached:
            return {**cached, "track": track, "artist": artist, "total_ms": total_ms}

        # 2. Kaggle exact
        exact = self.kaggle.exact_lookup(norm)
        if exact:
            result = self._build(track, artist, total_ms,
                                 exact["energy"], exact["valence"],
                                 SOURCE_EXACT, exact["genre"])
            self.cache.set(cache_key, result)
            return result

        # 3. Kaggle fuzzy
        fuzzy = self.kaggle.fuzzy_lookup(norm)
        if fuzzy:
            entry, score, matched = fuzzy
            result = self._build(track, artist, total_ms,
                                 entry["energy"], entry["valence"],
                                 SOURCE_FUZZY, entry["genre"],
                                 match_score=score, matched_key=matched)
            self.cache.set(cache_key, result)
            return result

        # 4. Gemini
        genre    = self.kaggle.detect_genre(artist)
        examples = self.kaggle.calibration_examples(genre, n=10)
        pred     = self.gemini.predict(track, artist, examples)
        if pred:
            result = self._build(track, artist, total_ms,
                                 pred["energy"], pred["valence"],
                                 SOURCE_GEMINI, genre)
            self.cache.set(cache_key, result)
            return result

        # 5. Default
        log.warning(f"All methods failed: '{track}' — using neutral 0.5/0.5")
        result = self._build(track, artist, total_ms, 0.5, 0.5, SOURCE_DEFAULT, "unknown")
        self.cache.set(cache_key, result)
        return result

    def lookup_batch(self, songs: list) -> list:
        results = []
        total   = len(songs)
        for i, song in enumerate(songs, 1):
            results.append(self.lookup(
                track    = song["track"],
                artist   = song["artist"],
                total_ms = song.get("total_ms", 0),
            ))
            if i % 50 == 0 or i == total:
                log.info(f"Batch: {i}/{total}")
        return results

    def stats(self) -> dict:
        return {
            "kaggle_index_size": len(self.kaggle.exact_map),
            "cache":             self.cache.stats(),
        }

    @staticmethod
    def _build(track, artist, total_ms, energy, valence, source, genre,
               match_score=None, matched_key=None) -> dict:
        return {
            "track":       track,
            "artist":      artist,
            "total_ms":    total_ms,
            "energy":      round(energy,  4),
            "valence":     round(valence, 4),
            "source":      source,
            "genre":       genre,
            "match_score": match_score,
            "matched_key": matched_key,
        }
