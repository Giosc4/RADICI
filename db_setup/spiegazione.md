# Spiegazione della directory `db_setup`

Questa directory contiene script eterogenei per il popolamento e la gestione iniziale del database Redis, oltre a strumenti per scaricare immagini da manifest IIIF. Sembra essere un ambiente di staging o di setup parallelo rispetto a `database_setup`, operando spesso sul DB Redis numero 10.

## Descrizione dei File

### Gestione Redis e Importazione Dati

- **`get_new_json_entries.py`**:
  - Legge un file JSONLines (`lodovico.jsonl`) contenente l'export dell'archivio Lodovico.
  - Per ogni entrata, se appartiene al "Progetto Radici":
    - Analizza l'URL IIIF per estrarre e scaricare le immagini ad alta risoluzione.
    - Costruisce un oggetto con i metadati (titolo, autore, data, origine, ecc.).
    - Inserisce l'oggetto in Redis (DB 10) usando l'ID dell'immagine come chiave.
  - Gestisce la conversione di liste e tipi complessi in stringhe per la compatibilità con Redis.

- **`redis_init.py`**:
  - Inizializza il database Redis (DB 10) svuotandolo (`flushdb`).
  - Carica massivamente dati da un file CSV (`dataset_with_embeddings_29_09_2025.csv`).
  - Usa `hmset` (deprecato ma funzionante) per salvare le righe del CSV come hash.

- **`redis_json_import.py`**:
  - Script di utilità per aggiornare le coordinate geografiche in Redis.
  - Legge un file GeoJSON (`objects_and_coordinates_29_09_2025.geojson`).
  - Per ogni feature nel GeoJSON, cerca la chiave corrispondente in Redis e aggiorna (o aggiunge) il campo `coordinates`.

### Elaborazione Immagini e Arricchimento

- **`setup_new_entries.py`**:
  - Script di post-processing che itera su tutte le chiavi in Redis (DB 10).
  - **Embeddings**: Se mancano, calcola gli embedding delle immagini usando **PyTorch** e **ResNet50** (differisce da script simili in altre directory che usano TensorFlow).
  - **Geocoding**: Se mancano le coordinate ma c'è un campo `place`, usa l'API di **OpenCage** per ottenere lat/long e salvare nel DB.

- **`img_embeddings.py`**:
  - Versione basata su **TensorFlow/Keras** e ResNet50 per calcolare embeddings.
  - Analoga a quella presente in `database_setup`. Legge i path delle immagini da un CSV e salva i risultati in un nuovo CSV.

### Download Immagini

- **`get_iiif_img_manifest.py`**:
  - Script specifico per scaricare immagini da manifest IIIF (testato su `unipr.jarvis.memooria.org`).
  - Naviga la struttura del manifest (sequences -> canvases -> images) per trovare l'URL del servizio immagini e scaricare il file.

- **`img_scrapper.py`**:
  - Scarica immagini da una lista di URL presenti in un file CSV (`db_archives_07_03_2025.csv`).
  - Utile per scaricare in bulk le immagini referenziate nei metadati.

### Altri File

- `img_embeddings copie.py`, `img_scrapper copie.py`: Copie di backup degli script omonimi.
