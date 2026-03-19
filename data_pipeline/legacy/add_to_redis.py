import redis
import json
import csv

redis_client = None

def connect_to_redis():
    global redis_client

    try:
        redis_client = redis.StrictRedis(host='192.168.249.189', port=6379, decode_responses=True, db=0)
        redis_client.ping()  # Check if the Redis server is reachable

        # Flush the database (delete all content)
        redis_client.flushdb()  # WARNING: This will delete all data in db=0
        print("Database has been flushed. All data is deleted.")

    except redis.ConnectionError as e:
        print(f"Redis connection failed: {e}")
        # TODO figure out what to do in this case
        redis_client = None  # Use a fallback or handle unavailable Redis scenario


def flatten_json(nested_json, prefix="", archive=""):
    """Flatten JSON object to store fields individually in Redis."""
    flat_dict = {}


    # Define field name mappings (original → renamed)
    field_mapping = {
        "places_relations_ssim[0]": "place",
        "places_relations_ssm[0]": "place",
        "http://schema.org/:locationCreated[0].@value": "place",
        "DOP_LUOGO": "place",
        "provenance_ssi": "origin",
        "tree_ancestor_path": "origin",
        "http://schema.org/:isPartOf[0].display": "origin",
        "type[0]": "type",
        "dcterms:type[0].@value": "type",
        "people_relations_ssim[0]": "author",
        "people_relations_ssm[0]": "author",
        "http://schema.org/:author[0].@value": "author",
        "DOP_INTERPRETI": "singer",
        "DOP_AUTORI": "author",
        "title": "title",
        "o:title": "title",
        "DOP_TITOLOOPERA": "title",
        "DOP_TITOLOBRANO": "title_song",
        "DOP_DATA": "date",
        "date": "date",
        "http://schema.org/:dateCreated[0].@value": "date",
        "DOP_URLSCH": "url_audio",
        "DOP_URLAUDIO": "url_audio",
        "DOP_URLIMG": "url",
        "cover_ts": "url",
        "thumbnail_display_urls.large": "url",
        "o:id": "id",
        "ID_DISCO": "id"
    }

    def recurse(json_obj, parent_key):
        if isinstance(json_obj, dict):
            for k, v in json_obj.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                # Apply renaming if the key is in the mapping
                new_key = field_mapping.get(new_key, new_key)
                recurse(v, new_key)
        elif isinstance(json_obj, list):
            for index, item in enumerate(json_obj):
                new_key = f"{parent_key}[{index}]"
                # Apply renaming if the key is in the mapping
                new_key = field_mapping.get(new_key, new_key)
                recurse(item, new_key)
        elif isinstance(json_obj, bool):  # Convert booleans to strings
            flat_dict[parent_key] = str(json_obj).lower()
        elif json_obj is None:  # Handle NoneType values
            flat_dict[parent_key] = "null"  # Or use "" if you prefer empty strings
        else:
            flat_dict[parent_key] = json_obj

    recurse(nested_json, prefix)
    flat_dict["archive"] = archive
    return flat_dict

def create_item(pipe, item, identifier, archive):

    """Store each item as a Redis hash."""
    item_id = item[identifier]  # Unique identifier
    key = f"item:{item_id}"  # Redis key for the hash

    flat_item = flatten_json(item, archive=archive)  # Flatten the JSON structure
    if not flat_item:
        print(f"Skipping empty item: {key}")
        return

    # print(flat_item)

    # print(f"Storing item with key: {key}")  # Debugging output
    pipe.hset(key, mapping=flat_item)  # Store the entire item as a hash

if __name__ == '__main__':
    connect_to_redis()

    # load cdc_extracted_items.json
    with open("cdc_extracted_items.json", "r", encoding="utf-8") as file:
        json_data_cdc = json.load(file)  # Load JSON as Python list/dict

    # load lodovico.jsonl
    with open("lodovico.jsonl", "r", encoding="utf-8") as file:
        json_data_lodo = [json.loads(line) for line in file]


    # Use pipeline for bulk insertion
    with redis_client.pipeline() as pipe:
        identifier_cdc = "o:id"
        identifier_lodo = "id"
        identifier_bene = "ID_DSCOPR"
        for i, item in enumerate(json_data_lodo):
            # pipe = create_fields(pipe, item)
            create_item(pipe, item, identifier_lodo, "lodovico")
        for item in json_data_cdc:
            # pipe = create_fields(pipe, item)
            create_item(pipe, item, identifier_cdc, "classense")
        # load BENEDETTI/...csv
        with open("BENEDETTI/DISCHI_OPERE.csv", "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                #item = json.dumps(row, ensure_ascii=False)  # Convert row to JSON
                create_item(pipe, row, identifier_bene, "benedetti")

        pipe.execute()  # Execute the batch insert

    print("Data inserted into Redis successfully!")