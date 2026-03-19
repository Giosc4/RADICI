import csv
import requests
import time
import re
import json
import pandas as pd

INPUT_FILE = 'db_archives_13_03_2025.csv'
OUTPUT_FILE = 'dataset_with_embeddings_23_05_2025.csv'
GEOJSON_FILE = 'objects_and_coordinates.geojson'

HEADERS_MB = {
    "User-Agent": "OperaGeoLocator/1.0 (youremail@example.com)"
}

HEADERS_WD = {
    "Accept": "application/sparql-results+json"
}

def parse_coordinates(coord_str):
    """
    Parse 'Point(LONG LAT)' into separate float values.
    """
    match = re.match(r'Point\(([-\d.]+) ([-\d.]+)\)', coord_str)
    if match:
        lon, lat = match.groups()
        return float(lon), float(lat)
    return None, None

def search_wikidata_work(work_title, composer_name):
    work_title = "|".join(work_title.lower().split())
    composer_name = "|".join(composer_name.lower().split())

    endpoint_url = "https://query.wikidata.org/sparql"
    query = f"""
        SELECT ?workLabel ?composerLabel ?place ?placeLabel ?coord WHERE {{
            ?work wdt:P31/wdt:P279* wd:Q2188189;    # musical work
                    rdfs:label ?workLabel;
                    wdt:P86 ?composer;
                    wdt:P4647 ?place.                 # location of creation

            ?composer rdfs:label ?composerLabel.

            OPTIONAL {{ ?place wdt:P625 ?coord. }}    # geo-coordinates

            FILTER(REGEX(LCASE(?workLabel), "{work_title.lower()}", "i"))
            FILTER(REGEX(LCASE(?composerLabel), "{composer_name.lower()}", "i"))

            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en,fr". }}
        }}
        LIMIT 1
    """

    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "OperaGeoLocator/1.0 (your-email@example.com)"
    }

    response = requests.get(endpoint_url, params={'query': query}, headers=headers)

    if response.status_code != 200:
        print("Query failed:", response.status_code)
        return []

    results = response.json()["results"]["bindings"]
    if not results:
        return None

    coord_str = results[0].get("coord", {}).get("value", "")
    lon, lat = parse_coordinates(coord_str)
    place_label = results[0].get("placeLabel", {}).get("value", "")
    return {"place": place_label, "lon": lon, "lat": lat}

df = pd.read_csv(INPUT_FILE)
with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

# Create set of existing IDs to avoid duplicates
existing_ids = set(f["properties"]["id"] for f in geojson_data["features"] if "id" in f["properties"])

for index, row in df.iterrows():
    if row.get('archive') != 'benedetti':
        continue

    row_id = str(row.get("id", "")).strip()
    if not row_id or row_id in existing_ids:
        continue

    title = row.get('title')
    author = row.get('author')
    singer = row.get('singer')

    if pd.isna(title) or pd.isna(author):
        continue

    print(f"🔍 Looking up: {title} by {author} (index {index})")
    geo_info = search_wikidata_work(title, author)
    time.sleep(1.5)  # Respectful pause between requests

    if geo_info and geo_info["lon"] and geo_info["lat"]:
        new_feature = {
            "type": "Feature",
            "properties": {
                "place": geo_info["place"],
                "type": "Music",
                "date": row.get("date", ""),
                "id": row_id,
                "archive": row.get("archive", ""),
                "url": row.get("url", ""),
                "img_path": row.get("img_path", ""),
                "author": author,
                "title": title,
                "singer": singer,
                "origin": row.get("origin", "")
            },
            "geometry": {
                "type": "Point",
                "coordinates": [geo_info["lon"], geo_info["lat"]]
            }
        }

        geojson_data["features"].append(new_feature)
        existing_ids.add(row_id)

        # ✅ Save progress after each successful addition
        with open(GEOJSON_FILE, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Added: {title} [{row_id}]")
    else:
        print(f"❌ No coordinates found for: {title} by {author}")