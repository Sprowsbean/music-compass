import pandas as pd

df = pd.read_csv("dataset2.csv")
df = df[["name", "artists", "album", "energy", "valence", "duration_ms"]]  # keep only these
df.to_csv("file.csv", index=False)
