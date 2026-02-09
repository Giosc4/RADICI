# Spiegazione della directory `docker_preparedb`

Questa directory contiene script progettati probabilmente per essere eseguiti all'interno di un container Docker (visti i path assoluti come `/app/data/`). Gli script gestiscono l'esportazione dati da Redis e la preparazione del database per l'uso in produzione o visualizzazione.

## Descrizione dei File

### Esportazione Dati

- **`export_db.py`**:
  - Si connette a Redis (DB 10).
  - Scansiona tutte le chiavi e recupera i dati.
  - **Esportazione CSV**: Salva tutti i dati in `/app/data/redis_export.csv`, rilevando dinamicamente i nomi delle colonne.
  - **Esportazione GeoJSON**: Crea `/app/data/redis_export.geojson` convertendo le coordinate salvate e formattando le proprietà per la mappa (invertendo lat/long per il formato GeoJSON). Pulizia dei campi (rrimuove le virgolette non necessarie).

### Preparazione e Arricchimento Database

- **`prepareDB.py`**:
  - Lavora principalmente su file CSV e JSON (`db_archives...csv`, `objects_and_coordinates.json`, `dataset_with_embeddings.csv`).
  - **Embeddings**: Verifica se esistono già embeddings per gli ID nel CSV. Se mancano, li calcola usando **TensorFlow/Keras** con **ResNet50**. Gestisce logiche specifiche per l'archivio "benedetti" (musica).
  - **GeoJSON**: Unisce i dati del CSV con le coordinate presenti nel file JSON per generare un nuovo file `objects_and_coordinates_29_09_2025.geojson` completo di metadati.

- **`setup_new_entries.py`**:
  - Script per l'aggiornamento massivo delle entrare in Redis (DB 10).
  - **Embeddings**: Usa **TensorFlow/Keras** (ResNet50) per calcolare gli embeddings delle immagini se mancanti. (Nota: include import di PyTorch inutilizzati o commentati, suggerendo un porting da/verso l'altra versione dello script).
  - **Geocoding**: Utilizza l'API **OpenCage** per ottenere coordinate dai nomi dei luoghi (`place`) se il campo `coordinates` è vuoto. Implementa una cache locale in Redis (`place_coordinates_cache`) per risparmiare chiamate API.
  - Salva i risultati aggiornati direttamente in Redis.

- **`setup_new_entries_10_2025.py`**:
  - Versione alternativa o datata di `setup_new_entries.py`.
  - Le differenze sembrano minime, principalmente nella gestione della decodifica delle stringhe da Redis.

### Altri File

- `docker_preparedb`: Probabilmente un Dockerfile o uno script shell (senza estensione) per orchestrare l'esecuzione nel container.
