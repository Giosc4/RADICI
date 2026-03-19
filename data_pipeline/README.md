# Data Pipeline

This directory contains the scripts used to collect, import, enrich, and export the project dataset outside of the web application runtime.

## Purpose

The `data_pipeline` area exists to keep data operations clearly separated from the Flask application.

Use it when you need to:

- fetch or collect new source material
- import records into Redis
- enrich records with coordinates or embeddings
- export Redis into CSV or GeoJSON

Do not use it as the normal application entry point for running the web interface.

## Structure

- `harvest/`
  Source acquisition scripts.
- `import/`
  Redis import and synchronization scripts.
- `enrich/`
  Data enhancement scripts such as geocoding and embedding generation.
- `export/`
  Export scripts for frontend-ready or analysis-ready outputs.
- `docker/`
  Container support for batch data operations.
- `legacy/`
  Historical or superseded scripts kept only for reference.

## Important Note

Several legacy files still contain hardcoded paths, hostnames, or API-related assumptions from earlier project phases. Review and parameterize them before reusing them in active workflows.

## Operational Model

The data pipeline does not replace Redis. Instead, it prepares and mutates the dataset that Redis stores.

The normal conceptual flow is:

1. collect or receive source data
2. import base records into Redis `DB 10`
3. enrich existing Redis records
4. export Redis into CSV or GeoJSON when needed
5. let Redis persist its own snapshot as an `.rdb` file

This means the pipeline scripts do not directly write the canonical Redis dump file. The `.rdb` snapshot is produced by Redis persistence after the dataset has already been loaded into Redis.

## Which Script Creates the Base Dataset

The main active dataset-creation script is:

- [import/import_jsonl_entries_to_redis.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/import/import_jsonl_entries_to_redis.py)

This script is the closest thing to a primary seed step for the object dataset in Redis.

It:

- reads a JSONL source export
- filters entries that belong to the RADICI scope
- requests IIIF manifests
- extracts image URLs from those manifests
- downloads local image files
- normalizes selected metadata fields
- writes one Redis hash per imported object or image

The hashes it creates form the working base dataset later used by the application.

## Active Script Responsibilities

### `harvest/`

- [harvest/harvest_classense_items.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/harvest/harvest_classense_items.py)
  Collects raw paginated item data from the Classense API and writes a local JSON file.
- [harvest/harvest_benedetti_media.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/harvest/harvest_benedetti_media.py)
  Downloads source PDFs, preview JPGs, and MP3 files for Benedetti records.
- [harvest/download_iiif_manifest_images.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/harvest/download_iiif_manifest_images.py)
  Downloads image assets from IIIF manifests for source preparation tasks.

### `import/`

- [import/import_jsonl_entries_to_redis.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/import/import_jsonl_entries_to_redis.py)
  Creates the initial Redis object records.
- [import/import_geojson_coordinates_to_redis.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/import/import_geojson_coordinates_to_redis.py)
  Adds or updates coordinates for records that already exist in Redis.

### `enrich/`

- [enrich/enrich_redis_entries.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/enrich/enrich_redis_entries.py)
  Backfills missing embeddings and coordinates for records already stored in Redis.
- [enrich/generate_image_embeddings.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/enrich/generate_image_embeddings.py)
  Supports standalone embedding generation workflows from local image sets.
- [enrich/enrich_benedetti_coordinates_from_wikidata.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/enrich/enrich_benedetti_coordinates_from_wikidata.py)
  Retrieves coordinate data for Benedetti-oriented records from an external source.

### `export/`

- [export/export_redis_to_csv_geojson.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/export/export_redis_to_csv_geojson.py)
  Reads Redis `DB 10` and exports its contents to CSV and GeoJSON.

## How the Redis Dump Fits In

The canonical snapshot currently tracked by the project is:

- [../data/redis/radici-redis-dump.rdb](/media/data/giacomo.vallasciani/RADICI/data/redis/radici-redis-dump.rdb)

That file should be understood as a persisted Redis state, not as the direct output of a pipeline script.

In practice:

- import scripts create records in Redis
- enrichment scripts complete those records
- export scripts generate file-based derivatives
- Redis persistence generates the `.rdb` snapshot

## Legacy Initialization Scripts

Some files under `legacy/` show earlier dataset bootstrapping approaches:

- [legacy/redis_init_legacy.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/legacy/redis_init_legacy.py)
  Imports from CSV into Redis and flushes the target DB first.
- [legacy/add_to_redis.py](/media/data/giacomo.vallasciani/RADICI/data_pipeline/legacy/add_to_redis.py)
  Loads multiple source formats into Redis using an older normalization approach.

These scripts are useful for historical context but are not the recommended active workflow.
