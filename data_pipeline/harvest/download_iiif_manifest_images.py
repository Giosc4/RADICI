import requests
import os
import json
import urllib.parse

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

def construct_image_url(image_service_url, width=800, height=400, format='jpg'):
    """Construct a IIIF image URL for the given image service."""
    return f"{image_service_url}/full/{width},/0/default.{format}"

def harvest_images_from_manifest(manifest_url, save_dir):
    """Harvest all image URLs from the IIIF manifest and download them."""
    # Request the manifest JSON
    try:
        response = requests.get(manifest_url)
        manifest_data = response.json()
    except Exception as e:
        print(f"Error fetching manifest: {e}")
        return

    # Ensure the save directory exists
    os.makedirs(save_dir, exist_ok=True)

    # Iterate through the canvases and images in the manifest
    for sequence in manifest_data.get('sequences', []):
        for canvas in sequence.get('canvases', []):
            # Use the canvas @id as the filename (strip URL characters and add .jpg)
            canvas_id = canvas.get('@id').split('/')[-1]  # Get the last part of the URL (canvas ID)
            canvas_filename = f"{canvas_id}.jpg"  # Add the .jpg extension

            print(f"Processing canvas: {canvas_filename}")

            # Iterate through the images associated with this canvas
            for image_annotation in canvas.get('images', []):
                image_service_url = image_annotation.get('resource', {}).get('service', {}).get('@id')
                if image_service_url:
                    # Construct the image URL using the IIIF image service
                    image_url = construct_image_url(image_service_url)

                    # Construct the file path to save the image
                    image_save_path = os.path.join(save_dir, canvas_filename)

                    # Download and save the image
                    download_image(image_url, image_save_path)

# Example usage
manifest_url = "https://unipr.jarvis.memooria.org/meta/iiif/67df13dc-6725-4cd8-ab5f-4e7778119c39/manifest"
save_directory = "./downloaded_images"

harvest_images_from_manifest(manifest_url, save_directory)

