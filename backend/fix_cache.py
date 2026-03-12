import json
from pathlib import Path

cache_path = Path("backend/data/cache/score_cache.json")

# Try alternate path if running from inside backend/ folder
if not cache_path.exists():
    cache_path = Path("data/cache/score_cache.json")

if not cache_path.exists():
    print("❌ Cache file not found")
    exit(1)

with open(cache_path, encoding="utf-8") as f:
    data = json.load(f)

before = len(data)
cleaned = {k: v for k, v in data.items() if v.get("source") != "default"}
after = len(cleaned)

with open(cache_path, "w", encoding="utf-8") as f:
    json.dump(cleaned, f, indent=2, ensure_ascii=False)

print(f"✓ Removed {before - after} bad 0.5/0.5 entries")
print(f"✓ Kept {after} good Kaggle entries")
print(f"✓ Cache cleaned — restart uvicorn now")