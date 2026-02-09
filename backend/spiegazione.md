# Spiegazione della directory `backend`

Questa directory contiene il codice sorgente per il backend dell'applicazione, sviluppato utilizzando **Flask**. Il backend gestisce le richieste API per la ricerca di immagini (tramite similarità visiva e parole chiave) e serve i file statici delle immagini.

Utilizza **FAISS** (Facebook AI Similarity Search) per l'indicizzazione e la ricerca rapida di vettori di embedding, e **SentenceTransformers** per generare embedding testuali.

## Descrizione dei File

### `app.py`

È il punto di ingresso principale dell'applicazione backend. Configura il server Flask, carica i modelli e gli indici, e definisce gli endpoint API.

**Funzionalità principali:**

- **Inizializzazione:**
  - Inizializza l'app Flask e abilita CORS.
  - Carica il modello `SentenceTransformer("all-MiniLM-L6-v2")`.
  - Verifica l'esistenza degli indici FAISS (`INDEX_PATH`, `INDEX_KW_PATH`) e dei file di dati (`EMBEDDINGS_PATH`, `KEYWORDS_PATH`), caricandoli o creandoli se necessario.
  - Scarica le risorse necessarie per NLTK (tokenizers, stopwords).
- **Gestione Indici:**
  - Carica/Costruisce l'indice per la ricerca visuale basata sugli embedding delle immagini.
  - Carica/Costruisce l'indice per la ricerca testuale basata sulle parole chiave estratte dai metadati (titolo, autore, ecc.).
- **Endpoints:**
  - `GET /images/<image_file>`: Restituisce un'immagine specifica dalla directory `downloaded_images`. Se l'immagine non esiste, restituisce `default.jpeg`.
  - `GET /images/`: Restituisce l'immagine di default.
  - `POST /search`: Accetta un JSON con `image_id`. Cerca l'embedding corrispondente a quell'ID e restituisce le immagini visivamente simili utilizzando `find_similar_images`. Gestisce casi di errore e valori nulli.
  - `GET /search_keywords`: Accetta un parametro di query `q`. Genera l'embedding della query, cerca nell'indice delle keywords (`index_keywords`) e restituisce i primi 10 risultati corrispondenti, recuperando i metadati associati.

**Funzioni Ausiliarie:**

- `extract_keywords_from_title(title)`: Pulisce, tokenizza e rimuove le stop words da un titolo.
- `extract_keywords_from_fields(row)`: Estrae keywords combinando vari campi (titolo, autore, model_base, origin, singer) di una riga del dataframe.

### `image_search.py`

Contiene la logica "core" per la gestione degli embedding e l'interazione con FAISS. Viene importato da `app.py`.

**Funzioni:**

- `load_embeddings(csv_path)`: Legge un file CSV contenente embeddings (salvati come stringhe), li parsa in array NumPy e filtra quelli non validi. Restituisce il DataFrame pulito e una matrice di embedding pronta per FAISS.
- `build_faiss_index(embedding_matrix)`: Crea un indice FAISS (`IndexFlatL2`) a partire dalla matrice di embedding. L2 indica che la ricerca si basa sulla distanza Euclidea.
- `find_similar_images(index, df, query_vec, top_k=5)`: Esegue la ricerca vera e propria. Dato un vettore di query (`query_vec`), trova i `top_k` vicini nell'indice e restituisce i metadati corrispondenti (titolo, autore, data, path immagine, ecc.) dal DataFrame.
- `search(...)`: Funzione simile a `find_similar_images` (sembra essere una versione precedente o alternativa usata per test diretti).

### Altri File

- `requirements.txt`: Elenca le dipendenze Python necessarie per eseguire il backend (flask, pandas, numpy, faiss-cpu, sentence-transformers, nltk, ecc.).
- `cert.pem` / `key.pem`: Certificati SSL per eseguire il server eventualmente in HTTPS.
- `info.txt`: Probabilmente contiene note o informazioni rapide sul deployment o configurazione.
- `__pycache__/`: Directory generata automaticamente da Python contenente i file di bytecode compilati.
