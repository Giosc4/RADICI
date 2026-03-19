import asyncio
from ollama import AsyncClient
import numpy as np
import pandas as pd
import string
import os
import re

client = AsyncClient(
    host='http://137.204.195.17:11434',
)
title = ""
author = ""

# Prompt
prompt01 = f'Tell me to which of the following category belongs this image entitled {title} from {author}: Architecture, Audiovisual, Design, Publishing, Photography, Music'
#prompt02 = 'Generate 4-5 keywords for this image'
prompt02 = 'Describe the image'

# Load DataFrame
df = pd.read_csv("db_archives_07_03_2025.csv")

# Build full image path
df["img_path"] = df["url"].apply(lambda x: os.path.basename(x) if isinstance(x, str) else None)
df["full_image_path"] = df["img_path"].apply(lambda x: os.path.join("downloaded_images", x) if x else None)

# Filter only rows with valid image paths
df = df[df["full_image_path"].apply(lambda x: os.path.isfile(x) if x else False)].reset_index(drop=True)

print(f"🖼️ Processing {len(df)} images...")

def extract_category(text):
    if not isinstance(text, str):
        return None

    categories = ["Architecture", "Audiovisual", "Design", "Publishing", "Photography", "Music"]
    category_pattern = "|".join(categories)
    
    # Match with "Answer"/"Category" before or after the word
    pattern = rf"""
        (?:
            (?:Answer|Category)[^a-zA-Z0-9"'`]*     # "Answer" or "Category" before
            [\*"'“”‘’`]*                            # Optional opening formatting: *, ", “
            (?P<cat1>{category_pattern})
            [\*"'“”‘’`]*                            # Optional closing formatting
            |
            [\*"'“”‘’`]*                            # Optional opening formatting
            (?P<cat2>{category_pattern})
            [\*"'“”‘’`]*[^a-zA-Z0-9"'`]*            # Optional closing formatting and punctuation
            (?:Answer|Category)                     # "Answer" or "Category" after
        )
    """

    match = re.search(pattern, text, re.IGNORECASE | re.VERBOSE)
    if match:
        cat = match.group("cat1") or match.group("cat2")
        return cat.capitalize()

    # Fallback: find all matches with or without quotes/formatting
    all_matches = re.findall(rf'[\*"`“”‘’]*\b({category_pattern})\b[\*"`“”‘’]*', text, re.IGNORECASE)
    if all_matches:
        return all_matches[-1].capitalize()

    return None


def extract_keywords_from_list(text):
    if not isinstance(text, str):
        return []

    keywords = []

    # 1) Extract bolded words from numbered or bulleted lists like 1. **Word**: or * **Word**:
    pattern_bold = r'(?:\d+\.|\*)\s*\*\*(\w+)\*\*'
    keywords += re.findall(pattern_bold, text)

    # 2) Extract quoted words from bullet points like • "Word" or • 'Word'
    if not keywords:
        pattern_quoted_bullet = r'•\s*["“”‘’\']([\w. ]+)["“”‘’\']'
        keywords += re.findall(pattern_quoted_bullet, text)

    # 2) Extract quoted words from bullet points like - "Word" or - 'Word'
    if not keywords:
        pattern_quoted_tiret = r'- \s*["“”‘’\']([\w. ]+)["“”‘’\']'
        keywords += re.findall(pattern_quoted_bullet, text)
    
     # 2) Extract quoted words from bullet points like * "Word" or * 'Word'
    if not keywords:
        pattern_quoted_tiret = r'\* \s*["“”‘’\']([\w. ]+)["“”‘’\']'
        keywords += re.findall(pattern_quoted_bullet, text)

    # 3) Extract comma-separated quoted list after a colon
    #    Matches things like: : "Notificazione", "A", "Macchittrato", "D. Macedra" and "Bartolomeo Zabara"
    if not keywords:
        pattern_comma_quoted = r':\s*((?:"[^"]+",?\s*)+(?:and\s*"[^"]+")?)'
        match = re.search(pattern_comma_quoted, text)
        if match:
            list_str = match.group(1)
            # Extract all quoted strings inside list_str
            quoted_items = re.findall(r'"([^"]+)"', list_str)
            keywords += quoted_items

    # 4) Fallback: If no keywords found, try to find first word after number/bullet without formatting
    if not keywords:
        fallback_pattern = r'(?:\d+\.|\*|•)\s*(\w+)'
        keywords += re.findall(fallback_pattern, text)

    if not keywords:
        pattern_loose_quoted = r'(?:"[^"]+",?\s*)+(?:and\s*"[^"]+")'
        loose_match = re.search(pattern_loose_quoted, text)
        if loose_match:
            quoted_items = re.findall(r'"([^"]+)"', loose_match.group(0))
            keywords += quoted_items

    # If still no keywords found, extract all words (cleaned)
    if not keywords:
        # Extract all words ignoring punctuation
        words = re.findall(r'\b\w[\w-]*\b', text)
        # Clean words: lowercase, strip punctuation (if any left)
        cleaned = [w.strip(string.punctuation).lower() for w in words if w.strip(string.punctuation)]
        # Deduplicate preserving order
        seen = set()
        deduped = []
        for w in cleaned:
            if w not in seen:
                deduped.append(w)
                seen.add(w)
        return deduped

    return keywords

async def get_image_description(image_path, prompt):
    
    image_description_content = ""  # Initialize a string to collect the response

    # Pass image as part of the query
    with open(image_path, 'rb') as image_file:  # Load your image
        image_data = image_file.read()

    message = {'role': 'user', 'content': prompt, "images": [image_path]}

    try:
        async for part in await client.chat(model='llama3.2-vision:11b', messages=[message], stream=True):
            text_part = part['message']['content']
            # print(text_part, end='', flush=True)
            image_description_content += text_part

    except Exception as e:
        print(f"Error while generating description: {e}")
        return None

    # Optionally extract part before "Note:"
    image_description_head, sep, tail = image_description_content.partition('Note:')

    return image_description_head.strip()  # or just `return image_description_content` if you want all of it

# Wrap in batch runner
async def process_all_images(df, prompt, category=False):
    results = []
    for idx, row in df.iterrows():
        title = row['title']
        author = row['author']
        prompt = f"Tell me to which of the following category belongs this image entitled {title} from {author}: Architecture, Audiovisual, Design, Publishing, Photography, Music"
        print(prompt)
        desc = await get_image_description(row["full_image_path"], prompt)
        if category:
            results.append(extract_category(desc))
        else:
            results.append(desc)
            #results.append(extract_keywords_from_list(desc))
        print(results)
    return results

# Run and assign to new column
async def main():
    print("Getting category...")    
    category = await process_all_images(df, "", False)
    df["category"] = category
    df.to_csv("df_with_category_29_05_2025.csv", index=False)

    #keywords = await process_all_images(df, prompt02)
    #df["keywords"] = keywords

    #df.to_csv("df_with_category_and_keywords.csv", index=False)
    print("✅ Descriptions saved.")

# Run the async main function
asyncio.run(main())
            
