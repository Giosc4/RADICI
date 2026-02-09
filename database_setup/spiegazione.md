# Spiegazione della directory `database_setup`

Questa directory contiene script per la preparazione, l'arricchimento e il caricamento dei dati nel database (Redis) e la generazione di file di supporto (GeoJSON, embeddings, metadati). Gli script interagiscono con diverse sorgenti dati (CSV, API esterne, modelli AI locale).

## Descrizione dei File

### Script di Gestione Database e Redis

- **`add_to_redis.py`**:
  - Si connette al database Redis locale.
  - Pulisce il database esistente (`flushdb()`).
  - Legge dati da diverse fonti: `cdc_extracted_items.json` (Classense), `lodovico.jsonl` e `BENEDETTI/DISCHI_OPERE.csv`.
  - Standardizza i nomi dei campi usando una mappa (es. `provenance_ssi` -> `origin`, `DOP_LUOGO` -> `place`).
  - Inserisce i dati in Redis come hash, usando una pipeline per efficienza.
  - Appiattisce i JSON annidati per salvarli in Redis.

- **`db_request.py`**:
  - Fornisce funzioni per interrogare Redis.
  - **Ricerca Testuale**: Utilizza `RediSearch` per cercare keyword nei campi titolo, autore, luogo, ecc.
  - **Ricerca per Immagini**: Recupera gli embedding delle immagini da Redis, costruisce un indice FAISS al volo (o lo aggiorna) e trova immagini simili basandosi sulla distanza Euclidea.

- **`geojson_setup.py`**:
  - Genera o aggiorna il file `updated_data.geojson` usato probabilmente per la visualizzazione su mappa.
  - Integra dati da un CSV (`db_archives_13_03_2025.csv`) nel GeoJSON esistente.
  - Gestisce le coordinate di fallback per i diversi archivi (Lodovico, Classense, Benedetti) se non specificate.

### Script di Arricchimento Dati e AI

- **`img_description.py`**:
  - Utilizza un modello multimodale locale (**Llama 3.2 Vision** tramite **Ollama**) per analizzare le immagini scaricate.
  - Genera due tipi di output per ogni immagine:
    1.  **Categoria**: Classifica l'immagine in una delle categorie predefinite (Architecture, Audiovisual, Design, Publishing, Photography, Music).
    2.  **Keywords**: Genera una descrizione o keywords (il prompt chiede "Describe the image" ma il codice contiene logica per estrarre keywords).
  - Salva i risultati progressivamente in `df_with_category_and_keywords.csv`.
  - _Nota_: Esistono versioni datate come `img_description_29_05_2025.py` che contengono lievi variazioni nei prompt o nella logica.

- **`img_embeddings.py`**:
  - Utilizza **TensorFlow/Keras** e il modello **ResNet50** pre-addestrato su ImageNet.
  - Estrae vettori di caratteristiche (embeddings) dalle immagini nella cartella `downloaded_images`.
  - Salva i path delle immagini e i relativi embeddings in `dataset_with_embeddings.csv`. Questi embeddings sono fondamentali per la ricerca di similarità visiva.

- **`request_musicbrainz_server.py`**:
  - Nonostante il nome, interroga principalmente **Wikidata** (tramite SPARQL).
  - Cerca coordinate geografiche per le opere musicali (titolo + autore/compositore), specificamente per l'archivio "Benedetti".
  - Arricchisce il file `objects_and_coordinates.geojson` con le nuove coordinate trovate.

### Scraping e Raccolta Dati

- **`benedetti_db.py`**:
  - Scraper specifico per l'archivio **Benedetti** (sito `ilcorago.org`).
  - Scarica PDF e file audio (MP3) associati ai record nel CSV.
  - Converte la prima pagina dei PDF in immagini JPG (thumbnail).
  - Gestisce i download con logiche di retry e pause casuali per non sovraccaricare il server.

- **`scraper.py`**:
  - Script semplice per scaricare dati JSON dall'API di **Classense** (`cdc.classense.ra.it`).
  - Itera su un numero prefissato di pagine e salva tutto in `extracted_items.json`.

### Altri File

- `img_description_23_05_2025.py`, `img_description_29_05_2025.py`, `img_description_29_05_2025_02.py`: Versioni precedenti o alternative dello script di descrizione immagini.
