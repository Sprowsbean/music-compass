"""
merge_datasets.py
-----------------
Merges 2 Spotify datasets into a single dataset.csv with only the columns
Music Compass needs: track_name, artists, energy, valence.

Usage (run from backend/):
    python merge_datasets.py

Expects:
    data/kaggle/dataset.csv        — your current 114k dataset (original)
    data/kaggle/dataset_1_2m.csv   — 1.2M track dataset

Output:
    data/kaggle/dataset.csv        — merged, deduplicated (overwrites original)
    data/kaggle/dataset_backup.csv — backup of your original
"""

import pandas as pd
from pathlib import Path
import shutil
import re

DATA_DIR = Path(".")

# ── Load ──────────────────────────────────────────────────────────────────────

print("Loading datasets...")

df1 = pd.read_csv(DATA_DIR / "dataset1.csv",       low_memory=False)
df2 = pd.read_csv(DATA_DIR / "dataset2.csv",  low_memory=False)

print(f"  Original:  {len(df1):>8,} rows  columns: {list(df1.columns)}")
print(f"  1.2M:      {len(df2):>8,} rows  columns: {list(df2.columns)}")

# ── Normalise to common schema ────────────────────────────────────────────────

def extract_cols(df, track_col, artist_col, album_col):
    """Pull only the 4 columns we need, rename to common schema."""
    out = df[[track_col, artist_col, album_col, "energy", "valence"]].copy()
    out.columns = ["track_name", "artists", "album_name", "energy", "valence"]
    return out

# adjust second arg if 1.2M dataset uses a different artist column name
df1 = extract_cols(df1, "track_name", "artists", "album_name")
df2 = extract_cols(df2, "track_name", "artists", "album_name")
# ── Normalise track names for dedup key ───────────────────────────────────────

_SUFFIX_RE = re.compile(
    r"\s*[\(\[]?"
    r"(?:sped[\s\-]*up|slowed|reverb|remaster(?:ed)?(?:\s+\d{4})?|"
    r"live|acoustic|remix|edit|version|radio[\s\-]*edit|"
    r"deluxe(?:\s+edition)?|anniversary|bonus track|"
    r"original[\s\-]*mix|extended[\s\-]*mix|"
    r"from\s+.+soundtrack)"
    r"[\)\]]?"
    r"(\s*-\s*.+)?$",
    re.IGNORECASE,
)
_FEAT_RE = re.compile(r"\s*[\(\[]?\s*(?:feat|ft|with)\.?\s+.+?[\)\]]?$", re.IGNORECASE)

def normalize(title: str) -> str:
    if not isinstance(title, str):
        return ""
    t = title.lower().strip()
    t = _FEAT_RE.sub("", t)
    t = _SUFFIX_RE.sub("", t)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# ── Merge — priority: df1 (original) > df2 (1.2M) ────────────────────────────

print("\nMerging...")

combined = pd.concat([df1, df2], ignore_index=True)

# Drop rows with missing essentials
combined = combined.dropna(subset=["track_name", "energy", "valence"])

# Build dedup key from normalised track name
combined["_key"] = combined["track_name"].apply(normalize)

# Keep first occurrence — df1 is first so its values win on conflicts
before = len(combined)
combined = combined.drop_duplicates(subset="_key", keep="first")
after = len(combined)

print(f"  Combined before dedup: {before:,}")
print(f"  Duplicates removed:    {before - after:,}")
print(f"  Final dataset size:    {after:,}")

# Drop the helper key column
combined = combined.drop(columns=["_key"])

# ── Save ──────────────────────────────────────────────────────────────────────

# Backup original first
backup_path = DATA_DIR / "dataset_backup.csv"
shutil.copy(DATA_DIR / "dataset1.csv", backup_path)
print(f"\nOriginal backed up to: {backup_path}")

# Write merged dataset
out_path = DATA_DIR / "dataset.csv"
combined.to_csv(out_path, index=False, encoding="utf-8")
print(f"Merged dataset saved to: {out_path}")
print("\nDone! Restart uvicorn to load the new dataset.")