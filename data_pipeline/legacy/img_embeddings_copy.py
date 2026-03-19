import numpy as np
import pandas as pd
import tensorflow as tf
import cv2
import os
import faiss
import matplotlib.pyplot as plt
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.models import Model

# Load the pre-trained ResNet50 model
base_model = ResNet50(weights="imagenet", include_top=False, pooling="avg")
model = Model(inputs=base_model.input, outputs=base_model.output)

# Function to load and preprocess an image
def extract_embedding(image_path):
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


image_folder = "downloaded_images"  # Folder containing images
# Load dataset
df = pd.read_csv("db_archives_07_03_2025.csv")  # Your CSV file should contain an 'image_path' column

# Create a new column with the full image path

# Extract only the filename from the URL
df["img_path"] = df["url"].apply(lambda x: os.path.basename(x) if isinstance(x, str) else None)

# Optional: Keep only JPG files (remove non-JPG entries)
df = df[df["img_path"].str.endswith(".jpg", na=False)]

df["img_path"] = df["img_path"].apply(lambda x: os.path.join(image_folder, x))  # Add folder path


#image_paths = [os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.endswith(".jpg")]

# Extract embeddings for all images
#image_embeddings = np.array([extract_embedding(img) for img in image_paths])

# Store embeddings using FAISS for fast similarity search
#index = faiss.IndexFlatL2(image_embeddings.shape[1])  # L2 (Euclidean) index
#index.add(image_embeddings)



# Extract embeddings for each image and store in a new column
df["embeddings"] = df["img_path"].apply(extract_embedding)
df["embeddings"] = df["embeddings"].apply(lambda x: str(x.tolist()))

# Save the DataFrame with embeddings
df.to_csv("dataset_with_embeddings.csv", index=False)

print("✅ Image embeddings successfully added to DataFrame and saved!")
