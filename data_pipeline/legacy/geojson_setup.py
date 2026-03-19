import math
import json
import pandas as pd

# Load the CSV file
#csv_df = pd.read_csv('df_with_category_and_keywords.csv')

# Load the CSV file
csv_main_df = pd.read_csv('db_archives_13_03_2025.csv', on_bad_lines='skip') 

# Load the GeoJSON file
with open('updated_data.geojson', 'r') as f:
     geojson = json.load(f)

# Load the GeoJSON file
# with open('objects_types_and_coordinates.geojson', 'r') as f:
#     geojson = json.load(f)

# Create lookup dictionaries
# types_map = dict(zip(csv_df['id'], csv_df['category']))
# url_map = dict(zip(csv_main_df['id'], csv_main_df['url']))
# original_types_map = dict(zip(csv_main_df['id'], csv_main_df['type']))

# cleaned_features = []

# def is_valid_geometry(geometry):
#     coords = geometry.get('coordinates')
#     if not coords:
#         return False
#     # Handle Point, LineString, Polygon differently if needed
#     return all(isinstance(c, (int, float)) for c in coords)

# for feature in geojson.get('features', []):
#     props = feature.get('properties', {})
#     feature_id = props.get('id')

#     prev_type = props.get('type')

#     category = None

#     if feature_id in types_map and isinstance(types_map[feature_id], str):
#         category = types_map[feature_id]
#     elif feature_id in original_types_map and isinstance(original_types_map[feature_id], str):
#         if prev_type == "manuscript":
#             category = "publishing" #original_types_map[feature_id]
#         elif prev_type == "object":
#             category = "design"
#         else:
#             category = prev_type

#     elif props.get('archive') == "benedetti":
#         category = 'music'

#     if category:
#         props['type'] = category.lower()

#     # Update 'url'
#     if feature_id in url_map:
#         props['url'] = url_map[feature_id]

#     if props.get('archive') == "benedetti":
#         props['url'] = f"http://www.ilcorago.org/benedetti/scheda.asp?id_disco={feature_id}"

#     # Replace NaN with empty string
#     for key, value in list(props.items()):
#         if isinstance(value, float) and math.isnan(value):
#             props[key] = ""

#     # Final inclusion test
#     if props.get('type') and is_valid_geometry(feature.get('geometry', {})):
#         feature['properties'] = props
#         cleaned_features.append(feature)


# # Save updated GeoJSONs
# geojson['features'] = cleaned_features

# Extract all IDs from the GeoJSON features
geojson_ids = {feature["properties"]["id"] for feature in geojson["features"]}

# Define fallback coordinates for each archive
archive_coords = {
    "lodovico": [10.9235478, 44.6464057],
    "classense": [12.1997037, 44.4145202],
    "benedetti": [12.2022038, 44.4183324]
}

# Add missing entries from DataFrame to GeoJSON
for _, row in csv_main_df.iterrows():
    item_id = row["id"]

    if item_id not in geojson_ids:
        archive = row.get("archive", "").lower()
        coords = archive_coords.get(archive, [0.0, 0.0])  # fallback if unknown archive

        feature = {
            "type": "Feature",
            "properties": {
                "place": row.get("place", ""),
                "type": row.get("type", ""),
                "date": row.get("date", ""),
                "id": item_id,
                "archive": archive,
                "url": row.get("url", ""),
                "img_path": row.get("img_path", ""),
                "author": row.get("author", ""),
                "title": row.get("title", ""),
                "singer": row.get("singer", ""),
                "origin": row.get("origin", "")
            },
            "geometry": {
                "type": "Point",
                "coordinates": coords
            }
        }

        geojson["features"].append(feature)

for feature in geojson.get('features', []):
    props = feature.get('properties', {})

    # Replace NaN with empty string
    for key, value in list(props.items()):
        if isinstance(value, float) and math.isnan(value):
            props[key] = ""

with open('updated_data.geojson', 'w') as f:
    json.dump(geojson, f, indent=2)