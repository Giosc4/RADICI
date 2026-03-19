import numpy as np
import pandas as pd
import tensorflow as tf
import cv2
import os
import json
import matplotlib.pyplot as plt
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.models import Model

# Function to load and preprocess an image
def extract_embedding(image_path):
    # Load the pre-trained ResNet50 model
    base_model = ResNet50(weights="imagenet", include_top=False, pooling="avg")
    model = Model(inputs=base_model.input, outputs=base_model.output)

    try:
        img = cv2.imread(image_path)  # Read image

        # Check if image is loaded successfully
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = cv2.resize(img, (224, 224))  # Resize to match ResNet input
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
        img = np.expand_dims(img, axis=0)  # Add batch dimension
        img = preprocess_input(img)  # Preprocess for ResNet

        embedding = model.predict(img)  # Extract feature vector
        return embedding.flatten()  # Convert to 1D vector

    except Exception as e:
        # Handle missing or incorrect files
        print(f"Error processing {image_path}: {e}")
        return np.zeros(2048)  # Return a vector of zeros for failed image embeddings

def check_value(value):
    if pd.isna(value):
        description = ""
    else:
        description = value
    return description

IMG_DIR = "/app/data/downloaded_images"  # Folder containing images
DB_CSV = "/app/data/db_archives_29_09_2025_CATEGORIES_CLEANED.csv" # Database in CSV format
EMBEDDINGS = "/app/data/dataset_with_embeddings.csv"  # Database updated with image embeddings
JSON_FILE = "/app/data/objects_and_coordinates.json"

categories = ['design', 'architecture', 'audiovisual','mode', 'photography', 'music', 'publishing', 'dance']

# STEP 1: GET MISSING embeddings and add to dataset
is_music_embeddings = False
img_music_embeddings = ""

# Load dataset
df = pd.read_csv(DB_CSV)
df_emb = pd.read_csv(EMBEDDINGS)
# Load your input JSON file
with open(JSON_FILE, 'r') as f:
    data_json = json.load(f)

# Extract only the filename from the URL
df["img_path"] = df["image"].apply(lambda x: os.path.basename(x) if isinstance(x, str) else None)
df["img_path"] = df["img_path"].apply(lambda x: os.path.join(IMG_DIR, x) if x is not None else None)  # Add folder path
# Drop rows where img_path is null
df = df.dropna(subset=['img_path'])

#ITERATE THROUGH DB, CHECK IF EMBEDDINGS ALREADY EXIST, OTHERWISE CREATE THEM
for i, row in df.iterrows():
    id_ = row['id']
    #emb = df_emb.loc[df_emb['id']==id_, 'embeddings']
    matching_rows = df_emb.loc[df_emb['id'] == id_, 'embeddings']

    if len(matching_rows) >= 1:
        emb = matching_rows.iloc[0]
    else:
        # Handle the case appropriately
        print(f"Expected exactly one match, but found {len(matching_rows)}.")
        emb = None

    # If no embeddings were computed, get Embeddings
    if emb == None:
        if row['img_path'] is not None:
            path = ""+row['img_path']
            if row['archive'] == 'benedetti':
                if is_music_embeddings:
                    img_embeddings = img_music_embeddings
                else:
                    img_embeddings = str(extract_embedding(path).tolist())
                    img_music_embeddings = img_embeddings
                    is_music_embeddings = True
            else:
                print("Extracting embeddings for ", row['title'])
                img_embeddings = str(extract_embedding(path).tolist())
        else:
            img_embeddings = None
    else:
        img_embeddings = emb

    df.at[i, "embeddings"] = img_embeddings



# Save the DataFrame with embeddings
df.to_csv("/app/data/dataset_with_embeddings_29_09_2025.csv", index=False)
print("✅ Image embeddings successfully added to DataFrame and saved!")


# Create a new column with the full image path

# STEP 2: SETUP GeoJson file
# Convert to GeoJSON
geojson = {
    "type": "FeatureCollection",
    "features": []
}

for item in data_json:

    longitude = item.get("longitude")
    latitude = item.get("latitude")
    
    # Skip object if coordinates are missing or invalid
    if longitude is None or latitude is None:
        continue
    try:
        item_df = df.loc[df['id']==item.get("id")]
        
        type_ = check_value(item_df['type'].item())
        date = check_value(item_df['date'].item())
        description = check_value(item_df['model_base'].item())
        fondo = check_value(item_df['fondo'].item())

        if not item_df.empty:
            feature = {
                "type": "Feature",
                "properties": {
                    "place": item.get("place", ""),
                    "type": type_, #item.get("type", ""),
                    "date": date,
                    "id": item.get("id", ""),
                    "fondo": fondo,
                    "description": description,
                    "archive": item.get("archive", ""),
                    "url": item.get("url", ""),
                    "img_path": item.get("img_path", ""),
                    "author": item.get("author", ""),
                    "title": item.get("title", ""),
                    "singer": item.get("singer", ""),
                    "origin": item.get("origin", "")
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(item["longitude"]), float(item["latitude"])]
                }
            }
            geojson["features"].append(feature)

    except ValueError:
        print(f"Skipping object with invalid coordinates: {item}")

# Save to GeoJSON file
with open('/app/data/objects_and_coordinates_29_09_2025.geojson', 'w') as f:
    json.dump(geojson, f, indent=2)

print("GeoJSON file saved as objects_and_coordinates_29_09_2025.geojson")
