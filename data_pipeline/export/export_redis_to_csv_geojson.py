import redis
import json
import csv
from pathlib import Path

# Connect to Redis DB 10
r = redis.StrictRedis(host='localhost', port=6379, db=10)

# Output file paths
csv_output_path = Path("/app/data/redis_export.csv")
geojson_output_path = Path("/app/data/redis_export.geojson")

# Step 1: Detect all field names in DB10
all_fields = set()
entries = {}

for key in r.scan_iter():
    key_str = key.decode()

    data = {k.decode(): v.decode() for k, v in r.hgetall(key).items()}
    if 'id' not in data:
        continue

    entries[key_str] = data
    all_fields.update(data.keys())

# Ensure 'id' exists as a fallback from the key if not present in the hash
#all_fields.add('id')
#fieldnames = sorted(all_fields | {'latitude', 'longitude'})  # Also include lat/lon if extracted
fieldnames = sorted(all_fields)

# Step 2: Export to CSV
with csv_output_path.open(mode='w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    
    for entry in entries.values():
        writer.writerow(entry)

    #for key, data in entries.items():
     #   row = data.copy()
      #  row.setdefault('id', key)  # Fallback to key as id

        # Parse coordinates to lat/lon
       # coords = row.get('coordinates')
       # try:
        #    coords_list = json.loads(coords) if coords else None
         #   if coords_list and len(coords_list) == 2:
          #      row['longitude'], row['latitude'] = coords_list
           # else:
            #    row['longitude'], row['latitude'] = None, None
        #except Exception:
         #   row['longitude'], row['latitude'] = None, None

#        writer.writerow(row)

# Step 3: Export to GeoJSON
geojson = {
    "type": "FeatureCollection",
    "features": []
}

for key, entry in entries.items():
    coords = entry.get('coordinates')
    try:
        coords_list = json.loads(coords) if coords else None
        if coords_list and len(coords_list) == 2:
            reversed_coords = [coords_list[1], coords_list[0]]
            properties = {
                    "place": entry.get("place"),
                    "type": entry.get("type"),
                    "date": entry.get("date"),
                    "id": entry.get("id"),
                    "fondo": entry.get("fondo"),
                    "description": entry.get("model_base"),
                    "archive": entry.get("archive"),
                    "url": entry.get("url"),
                    "img_path": entry.get("img_path"),
                    "author": entry.get("author"),
                    "title": entry.get("title"),
                    "singer": entry.get("singer"),
                    "origin": entry.get("origin")
                    }
            # Replace empty strings with None (null in JSON)
            #properties = {k: (v if v != "" else None) for k, v in properties.items()}

            properties = {k: (v.replace('\\"', '"') if isinstance(v, str) else v) if v != "" else None for k, v in properties.items()}

            feature = {
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": "Point",
                    "coordinates": reversed_coords
                }
            }
            geojson["features"].append(feature)

    except Exception as e:
        print(e)
        continue  # Skip if invalid

# Save GeoJSON file
with geojson_output_path.open('w', encoding='utf-8') as geojson_file:
    json.dump(geojson, geojson_file, indent=2, ensure_ascii=False)

print(f"✅ Exported:\n- CSV: {csv_output_path}\n- GeoJSON: {geojson_output_path}")

