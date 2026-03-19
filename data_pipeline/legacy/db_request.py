import redis
import json

import numpy as np
import faiss

from redis.commands.search.field import TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.search import Search

redis_client = None

def connect_to_redis():
    global redis_client

    try:
        redis_client = redis.StrictRedis(host='192.168.249.189', port=6379, decode_responses=True, db=0)
        redis_client.ping()  # Check if the Redis server is reachable
    except redis.ConnectionError as e:
        print(f"Redis connection failed: {e}")
        # TODO figure out what to do in this case
        redis_client = None  # Use a fallback or handle unavailable Redis scenario


def search_redis(keyword):
    matching_items = []
    
    for key in redis_client.scan_iter("item:*"):  # Scan all items
        item = redis_client.hgetall(key)  # Get item details
        if any(keyword.lower() in value.lower() for value in item.values()):
            matching_items.append(item)

    return matching_items

def search_with_redisearch_full(keyword):
    try:
        query = f'''@title:{keyword} | @author:{keyword} | @singer:{keyword} | @place:{keyword} | 
        @origin:{keyword} | @type:{keyword} | @date:{keyword}'''
        results = redis_client.ft("idx:items").search(query)
        return [doc.__dict__ for doc in results.docs]
    
    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}")
    except Exception as e:
        print(f"Error executing search: {e}")

def search_with_redisearch(keyword, max_res):
    try:
        query = f'''@title:{keyword} | @author:{keyword} | @singer:{keyword} | 
        @place:{keyword} | @origin:{keyword} | @type:{keyword} | @date:{keyword}'''

        # Specify only the required fields (title, url, and others) in the search results
        search_query = Query(query).return_fields("id", "title", "url", "url_audio", "author", "place", "type", "date", "origin", "embedding")

        # List to store all the results
        all_results = []

        # Keep track of the number of results fetched and the current start index
        start = 0
        page_size = 100  # Number of results per page

        while True:
            # Apply pagination (fetch 100 results at a time)
            results = redis_client.ft("idx:items").search(search_query.paging(start, page_size))

            # If there are no more results, break the loop
            if not results.docs:
                break

            # Extract only the required fields, using getattr() to handle missing fields
            extracted_results = [{
                "title": getattr(doc, "title", "No Title"),  # Default to "No Title" if field is missing
                "author": getattr(doc, "author", "Unknown Author"),  # Default to "Unknown Author" if field is missing
                "place": getattr(doc, "place", "Unknown Place"),  # Default to "Unknown Place" if field is missing
                "type": getattr(doc, "type", "Unknown Type"),  # Default to "Unknown Type" if field is missing
                "date": getattr(doc, "date", "Unknown Date"),  # Default to "Unknown Date" if field is missing
                "origin": getattr(doc, "origin", "Unknown Origin"),  # Default to "Unknown Origin" if field is missing
                "id": getattr(doc, "id", "Unknown ID"),
                "url": getattr(doc, "url", getattr(doc, "url_audio", "No URL"))  # Fallback to "url_audio" if "url" is missing
            } for doc in results.docs]
            all_results.extend(extracted_results)
            
            # Update the start index to fetch the next page
            start += page_size

        # Get the total count of objects found
        count = results.total

        return {"count": count, "results": extracted_results}

    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}")
        return {"count": 0, "results": []}
    except Exception as e:
        print(f"Error executing search: {e}")
        return {"count": 0, "results": []}

# Function to retrieve embeddings for a batch of images from Redis
def get_batch_image_embeddings(redis_client, batch_size=1000):
    image_embeddings = []
    image_ids = []
    cursor = 0

    while True:
        # Retrieve a batch of keys
        batch_keys = redis_client.scan(cursor=cursor, match='item:*', count=batch_size)[1]
        if not batch_keys:
            break

        # Fetch embeddings in a single batch
        keys_with_embeddings = redis_client.mget([f"{key}:embedding" for key in batch_keys])
        
        for key, embedding_str in zip(batch_keys, keys_with_embeddings):
            if embedding_str:
                embedding = json.loads(embedding_str)
                image_ids.append(key)
                image_embeddings.append(embedding)
        
        # Update cursor for scanning
        cursor = cursor + len(batch_keys)

    # Convert the list of embeddings into a numpy array (FAISS requires this format)
    image_embeddings = np.array(image_embeddings).astype(np.float32)
    return image_ids, image_embeddings

# Function to build a FAISS index
def build_faiss_index(image_embeddings):
    # Create a FAISS index for L2 (Euclidean) distance
    index = faiss.IndexFlatL2(image_embeddings.shape[1])
    index.add(image_embeddings)
    return index

# Function to find the most similar images based on a given image's embedding
def find_similar_images(query_embedding, image_embeddings, image_ids, top_k=5):
    # Create a FAISS index
    index = build_faiss_index(image_embeddings)

    # Convert the query embedding to a numpy array (FAISS requires the input to be float32)
    query_embedding = np.array(query_embedding).astype(np.float32).reshape(1, -1)

    # Search for the top_k most similar images
    distances, indices = index.search(query_embedding, top_k)

    # Return the top_k most similar images' ids and their distances
    similar_images = []
    for i in range(top_k):
        image_id = image_ids[indices[0][i]]
        distance = distances[0][i]
        similar_images.append({"image_id": image_id, "distance": distance})

    return similar_images

# Example of using the functions
def search_for_similar_images(redis_client, query_image_id, batch_size=1000, top_k=5):
    # Construct the Redis key for the image (ensure the key format matches what's in Redis)
    redis_key = f"{query_image_id}"

    # Retrieve the embedding for the query image
    query_embedding_str = redis_client.hget(redis_key, "embedding")

    if not query_embedding_str:
        print(f"Image {query_image_id} not found in Redis.")
        return []

    # Convert the query embedding from JSON string to a numpy array
    try:
        query_embedding = json.loads(query_embedding_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding embedding for {query_image_id}: {e}")
        return []

    # Get all image embeddings from Redis in batches
    try:
        image_ids, image_embeddings = get_batch_image_embeddings(redis_client, batch_size)
    except ConnectionError:
        print("Connection to Redis failed.")
        return []

    # Find the most similar images
    similar_images = find_similar_images(query_embedding, image_embeddings, image_ids, top_k=top_k)

    return similar_imagess


if __name__ == '__main__':
    connect_to_redis()
    word = input("Enter a keyword to search: ")
    search_results = search_with_redisearch(word, 5)
    print(f"Total objects found for '{word}': {search_results['count']}")
    print(json.dumps(search_results["results"], indent=4))

    print("GETTING SIMILAR IMAGE------------------------------------------------------------")

    # Example usage:
    query_image_id = search_results["results"][0]["id"]  # Replace with the image ID you want to search for
    print(query_image_id)
    similar_images = search_for_similar_images(redis_client, query_image_id)

    # Display the results
    print("Similar images:")
    for img in similar_images:
        print(f"Image ID: {img['image_id']}, Distance: {img['distance']}")

