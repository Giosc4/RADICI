import os
import requests
import pandas as pd
from tqdm import tqdm  # To show progress bar while downloading images
from urllib.parse import urlparse
import re

# Function to download image from URL
def download_image(url, save_path):
    try:
        # Get the image content from the URL
        response = requests.get(url, stream=True)
        
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Open the file to write the content
            with open(save_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Downloaded: {save_path}")
        else:
            print(f"Failed to download: {url}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

# Function to extract image filename from URL
def extract_image_filename(url):
    # Parse the URL to extract the path
    path = urlparse(url).path
    
    # Get the filename (last part of the path)
    filename = os.path.basename(path)
    
    # Optionally, you can sanitize the filename to remove unwanted characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)  # Remove any invalid characters for filenames
    return filename

# Function to scrape images based on DataFrame's 'image_url' column
def scrape_images(df, url_column, output_folder="downloaded_images"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)  # Create directory if not exists
    
    # Loop over each URL in the DataFrame
    for idx, row in tqdm(df.iterrows(), total=df.shape[0], desc="Downloading images"):
        image_url = row[url_column]  # Assuming the column in DataFrame contains image URLs
        if pd.notnull(image_url):
            # Extract filename from the URL
            image_name = extract_image_filename(image_url)
            
            # Create the full path for saving the image
            save_path = os.path.join(output_folder, image_name)
            
            # Download and save the image
            download_image(image_url, save_path)

df = pd.read_csv("db_archives_07_03_2025.csv")

# Scrape the images from the URL column and save them to the local folder
scrape_images(df, url_column="url", output_folder="downloaded_images")
