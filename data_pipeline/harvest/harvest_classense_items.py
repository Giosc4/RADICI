import json
import requests

# 212 pagine
# https://www.cdc.classense.ra.it/api/items?resource_class_id=33&page=0

data = []

page_num = 212

for i in range(page_num):
    print("Getting page", i+1)

    # URL of the API
    url = "https://www.cdc.classense.ra.it/api/items?resource_class_id=33&page=" + str(i)

    # Send a GET request to the API
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to retrieve data: {response.status_code}")
        break

    # Parse the JSON data
    page_data = response.json()

    data += page_data

# Save the extracted data to a JSON file
with open('extracted_items.json', 'w') as f:
    json.dump(data, f, indent=4)
