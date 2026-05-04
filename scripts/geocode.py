import pandas as pd
import json
import os
import ssl
import certifi
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# =========================
# PARAMETRES
# =========================
INPUT_FILE = "./data/example_data.csv"
OUTPUT_FILE = "./result/result_example.csv"
CACHE_FILE = "./result/geo_cache.json"

USE_CACHE_ONLY = False  

# =========================
# READ DATA
# =========================
df = pd.read_csv(INPUT_FILE)
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

df.columns = ["id", "species", "voivodeship", "county", "commune", "locality", "v1", "v2", "v3"]

print(f"LOADED RECORDS: {len(df)}")

# =========================
# CACHE
# =========================
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        results = json.load(f)
else:
    results = {}

# =========================
# GEOLOCATOR
# =========================
ctx = ssl.create_default_context(cafile=certifi.where())

geolocator = Nominatim(
    user_agent="zenodo_geo_pipeline",
    timeout=10,        # type: ignore
    ssl_context=ctx    # type: ignore
)

geocode = RateLimiter(
    geolocator.geocode,
    min_delay_seconds=1.1,
    max_retries=2
)

# =========================
# BUILD QUERIES
# =========================
df["query"] = (
    df["locality"].astype(str) + ", " +
    df["commune"].astype(str) + ", " +
    df["county"].astype(str) + ", " +
    df["voivodeship"].astype(str) + ", Poland"
)

unique_queries = df["query"].unique()
print(f"UNIQUE LOCALIZATIONS: {len(unique_queries)}")

# =========================
# GEOCODING
# =========================
for i, query in enumerate(unique_queries, 1):

    if query in results:
        continue

    if USE_CACHE_ONLY:
        results[query] = [None, None]
        continue

    print(f"[{i}/{len(unique_queries)}] {query}")

    try:
        location = geocode(query)  # type: ignore

        if location is not None:
            results[query] = [location.latitude, location.longitude]
        else:
            results[query] = [None, None]

    except Exception as e:
        print(f"Błąd: {e}")
        results[query] = [None, None]

    if i % 50 == 0:
        with open(CACHE_FILE, "w") as f:
            json.dump(results, f)

# zapis końcowy
with open(CACHE_FILE, "w") as f:
    json.dump(results, f)

# =========================
# MAPPING
# =========================
df["X"] = df["query"].map(lambda q: results.get(q, [None, None])[0])
df["Y"] = df["query"].map(lambda q: results.get(q, [None, None])[1])

df = df.drop(columns=["query"])

# =========================
# SAVING
# =========================
df.to_csv(OUTPUT_FILE, index=False)
print(f"\nSAVED: {OUTPUT_FILE}")