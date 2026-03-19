import os
import ast
import redis
import requests
import jsonlines
import json  # For converting lists to JSON strings

# Connect to Redis
r = redis.StrictRedis(host='localhost', port=6379, db=10)

def construct_image_url(image_service_url, width=800, height=400, format='jpg'):
    """Construct a IIIF image URL for the given image service."""
    return f"{image_service_url}/full/{width},/0/default.{format}"

# Function to convert lists and other complex types to strings
def convert_lists_to_strings(data):
    """Recursively convert lists (or other complex types) to JSON strings."""
    if isinstance(data, list):
        return json.dumps(data)  # Convert list to a JSON string
    elif isinstance(data, dict):
        return {k: convert_lists_to_strings(v) for k, v in data.items()}  # Recursively process dicts
    else:
        return data  # Return the value as is if it's not a list or dict

# Function to download the image and save it locally
def download_image(url, save_path):
    """Download image from the URL and save it locally."""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Image saved at {save_path}")
        else:
            print(f"Failed to download image: {url}")
    except Exception as e:
        print(f"Error downloading image {url}: {e}")

# Function to construct the IIIF image URL
def construct_image_url(image_service_url, width=800, height=400, format='jpg'):
    """Construct a IIIF image URL for the given image service."""
    return f"{image_service_url}/full/{width},{height}/0/default.{format}"

# Function to fetch image URLs from IIIF Manifest
def fetch_iiif_images(iiif_url):
    """Fetch the IIIF manifest and extract image URLs."""
    try:
        response = requests.get(iiif_url)
        response.raise_for_status()  # Check if request was successful
        manifest_data = response.json()
        
        # Look for the images in the manifest
        image_urls = []
        image_ids = []  # We also want to capture the IDs of the images
        
        for sequence in manifest_data.get('sequences', []):
            for canvas in sequence.get('canvases', []):
                canvas_id = canvas.get('@id').split('/')[-1]
                canvas_filename = f"{canvas_id}.jpg"

                for image_annotation in canvas.get('images', []):
                    image_service_url = image_annotation.get('resource', {}).get('service', {}).get('@id')
                    if image_service_url:
                    # Construct the image URL using the IIIF image service
                        image_url = construct_image_url(image_service_url)
                        image_urls.append(image_url)
                        image_ids.append(canvas_id)
        return image_urls, image_ids
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IIIF manifest from {iiif_url}: {e}")
        return [], []

        # Assuming that images are in the "sequences" or "canvases" sections of the manifest
        #for sequence in manifest_data.get("sequences", []):
        #    for canvas in sequence.get("canvases", []):
        #        if 'images' in canvas:
        #            for image in canvas['images']:
        #                image_url = image['resource']['@id']  # IIIF image URL
        #                image_id = image['resource']['@id'].split('/')[-1]  # Extract image ID from the URL
        #                image_urls.append(image_url)
        #                image_ids.append(image_id)  # Add the image ID for each image
        #return image_urls, image_ids  # Return both URLs and image IDs
    #except requests.exceptions.RequestException as e:
        #print(f"Error fetching IIIF manifest from {iiif_url}: {e}")
        #return [], []

# Function to process each entry
def process_entry(entry, save_dir):
    """Process each entry and map to the new structure."""
    # Check if the entry belongs to the correct collection
    if "Progetto Radici" in entry.get("collection", []):
        # Extract the relevant fields
        creator = entry.get("creator", [])
        date_ssim = entry.get("date_ssim", "")
        orgs_relations_ssim = entry.get("orgs_relations_ssim", [])
        places_relations_ssim = entry.get("places_relations_ssim", [])
        title = entry.get("title", "")
        description = entry.get("description", "")
        geo_ssm = entry.get("geo_ssm", [])
        collection = entry.get("collection", [])
        iiif_url = entry.get("iiif", "")

        if isinstance(geo_ssm, str):
            try:
                geo_ssm=ast.literal_eval(geo_ssm)
                if isinstance(geo_ssm, list):
                    geo_ssm = [float(coord) for coord in geo_ssm]
                else:
                    geo_ssm = []
            except (ValueError, SyntaxError):
                geo_ssm = []
        elif isinstance(geo_ssm, list):
            geo_ssm = [float(coord) for coord in geo_ssm if coord]
        
        if isinstance(date_ssim, list):
            date_ssim = "/".join(date_ssim)
        fondo = collection[0] if isinstance(collection, list) else collectiion
        # Fetch the image URLs and IDs from the IIIF manifest
        if iiif_url:
            image_urls, image_ids = fetch_iiif_images(iiif_url)
        else:
            image_urls = []
            image_ids = []

        # Create Redis entries for each image URL and ID
        for image_url, image_id in zip(image_urls, image_ids):
            # Construct local file path
            image_filename = f"{image_id}.jpg"  # Image name as image_id.jpg
            image_path = os.path.join(save_dir, image_filename)  # Local save path

            # Download the image
            download_image(image_url, image_path)

            # Prepare Redis entry
            redis_entry = {
                "archive": "Lodovico",  # Static value
                "author": creator[0] if creator else "",  # First creator
                "date": date_ssim,
                "id": image_id,  # Use the image ID for this entry
                "origin": orgs_relations_ssim[0] if orgs_relations_ssim else "",  # First origin
                "place": places_relations_ssim[0] if places_relations_ssim else "",  # First place
                "singer": "",  # No data given for singer in the example
                "title": title,
                "type": "architecture",  # Static value
                "url": f"https://lodovico-staging.medialibrary.it/media/schedadl.aspx?id={image_id}",
                "fondo": fondo,  # Leave as is for now; will be converted in convert function
                "image": image_filename,  # Use the saved image name
                "image_url": image_url,  # The actual image URL
                "model_base": description,  # Not provided
                "model_lora": "",  # Not provided
                "img_path": "/app/data/"+image_path,  # Local path to image
                "embeddings": "",  # Not provided
                "coordinates": geo_ssm if geo_ssm else "",  # Leave as is; will be converted in convert function
            }

            # Convert lists and complex types to strings
            redis_entry = convert_lists_to_strings(redis_entry)

            # Create a Redis key based on the image ID
            redis_key = f"{image_id}"  # Use image ID for the Redis key

            # Store the entry in Redis
            r.hset(redis_key, mapping=redis_entry)  # Use hset instead of deprecated hmset
            print(f"Entry saved in Redis with key {redis_key} for image {image_id}")

# Read the jsonl file and process entries
jsonl_file = 'lodovico-export-2025-10-09.jsonl'  # Replace with your file path
save_dir = 'downloaded_images'  # Directory where images will be saved
os.makedirs(save_dir, exist_ok=True)  # Ensure the save directory exists

with jsonlines.open(jsonl_file) as reader:
    for entry in reader:
        process_entry(entry, save_dir)

