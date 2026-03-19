import os
import redis
import requests
import json
from io import BytesIO
import torch
import cv2
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.models import Model
from torchvision import models, transforms
import numpy as np
from opencage.geocoder import OpenCageGeocode

# Initialize Redis connection (using DB 10)
r = redis.StrictRedis(host='localhost', port=6379, db=10, decode_responses=True)

cache_key = 'place_coordinates_cache'

# Initialize the OpenCage Geocoder (get your own API key)
OPEN_CAGE_API_KEY = 'd1b80372526b45da92d057b1654759c3'#'your_opencage_api_key'
geocoder = OpenCageGeocode(OPEN_CAGE_API_KEY)

# Load pre-trained model for extracting image embeddings (ResNet50)
#model = models.resnet50(pretrained=True)
#model.eval()

# Load the pre-trained ResNet50 model
base_model = ResNet50(weights="imagenet", include_top=False, pooling="avg")
model = Model(inputs=base_model.input, outputs=base_model.output)

# Define image transformation pipeline
#transform = transforms.Compose([
  #  transforms.Resize((256, 256)),
 #   transforms.ToTensor(),
#    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
#])
def extract_embeddings(image_path):
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
        return np.zeros(2048)

"""Extract embeddings from an image."""
#    try:
#        image = Image.open(image_path).convert('RGB')
#        image_tensor = transform(image).unsqueeze(0)  # Add batch dimension
#        with torch.no_grad():
#            embeddings = model(image_tensor)
# Return the flattened vector of embeddings
#        return embeddings.flatten().numpy()
#    except Exception as e:
#        print(f"Error extracting embeddings from {image_path}: {e}")
#        return None

def get_coordinates_from_place(place):
    """Get coordinates from a place name using OpenCage Geocoder."""
    try:
        cached = r.hget(cache_key, place)
        if cached:
            print(f"Using cached coordinates for '{place}'")
            return json.loads(cached)

        result = geocoder.geocode(place)
        if result:
            lat, lng = result[0]['geometry']['lat'], result[0]['geometry']['lng']
            coords = [lat, lng]
            r.hset(cache_key, place, json.dumps(coords))
            return [lat, lng]
        else:
            print(f"Could not find coordinates for place: {place}")
            return None
    except Exception:
        print(f"Error fetching coordinates for place {place}")
        return None

def process_entry(redis_key, entry):
    """Process each entry to update missing embeddings and coordinates."""
    # Extract existing fields
    image_path = entry.get('img_path')
    place = entry.get('place')
    embeddings = entry.get('embeddings')
    coordinates = entry.get('coordinates')

    # Check if embeddings are missing and extract if the image exists
    if not embeddings and image_path and os.path.exists(image_path):
        print(f"Extracting embeddings for image {entry['id']}...")
        embeddings = extract_embeddings(image_path)
        if embeddings is not None:
            # Save embeddings to Redis
            embeddings_list = embeddings.tolist()
            embeddings_json = json.dumps(embeddings_list)
            r.hset(redis_key, 'embeddings', embeddings_json)
            #r.hset(redis_key, 'embeddings', embeddings.tobytes())
            print(f"Embeddings for {entry['id']} saved in Redis.")

    # Check if coordinates are missing
    if ((not coordinates) or (coordinates=='[]')) and place:
        print(f"Fetching coordinates for place '{place}'...")
        coordinates = get_coordinates_from_place(place)
        if coordinates:
            # Save coordinates to Redis
            r.hset(redis_key, 'coordinates', json.dumps(coordinates))
            print(f"Coordinates for {entry['id']} saved in Redis: {coordinates}")

def safe_decode(byte_data):
    try:
        return byte_data.decode('utf-8')
    except UnicodeDecodeError:
        # Handle the error: You could skip or return a fallback value
        return f"<non-utf8: {byte_data}>"

def process_all_entries():
    """Process all entries in Redis DB 10."""
    print("Processing all entries")

    # Iterate through all keys using SCAN
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, count=10)  # Adjust count for more/less keys per call
        
        for key in keys:
            # Check if the key is a hash and retrieve the hash using hgetall
            if r.type(key) == 'hash':
                hash_value = r.hgetall(key)  # Returns a dictionary of field-value pairs from the hash
                
                # Process the key-value pair (you can perform your logic here)
                #print(f"Key: {key}, Hash: {hash_value}")
                process_entry(key, hash_value)
        
        # If cursor is 0, we are done scanning all the keys
        if cursor == 0:
            break

    
if __name__ == "__main__":
    process_all_entries()
