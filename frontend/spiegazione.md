# Spiegazione della directory `frontend`

Questa directory contiene il codice per l'interfaccia utente web dell'applicazione. L'applicazione visualizza gli oggetti (immagini e metadati) su una mappa interattiva (Mapbox) e in una griglia, permettendo l'esplorazione e la ricerca per similarità o keyword.

## Descrizione dei File

### HTML e Struttura

- **`index.html`**:
  - La pagina principale dell'applicazione.
  - Carica le librerie necessarie (Mapbox GL JS, Bootstrap, font personalizzati).
  - Definisce i contenitori principali: `#map` (mappa), `#sidebar_metamotor` (barra laterale per i risultati simili), `#search-box` (ricerca keyword), e le modali/popup.
  - Collega i file CSS (`style.css`) e JS (`map.js`, `grid.js`).

### Stile

- **`style.css`**:
  - Foglio di stile CSS personalizzato.
  - Definisce l'aspetto di:
    - **Mappa e Popup**: Stile personalizzato per i popup di Mapbox (colori arancioni, font 'Xanh Mono' e 'Martian Mono', pulsanti espandi).
    - **Sidebar**: Pannello laterale a comparsa per visualizzare i risultati (simili o dettagli).
    - **Filtri e Icone**: Stile per i bottoni dei filtri e le icone delle categorie (colori, hover effects).
    - **Griglia**: Layout per la visualizzazione a griglia (se utilizzata/attivata).

### Logica JavaScript

- **`map.js`**:
  - Gestisce la logica principale della mappa **Mapbox**.
  - **Caricamento Dati**: Recupera il GeoJSON (`redis_export.geojson` o `objects_types_and_coordinates.geojson`) contenente i punti da visualizzare.
  - **Clustering**: Raggruppa i punti vicini in cluster, mostrando icone diverse in base alla categoria dominante (musica, architettura, ecc.).
  - **Filtri**: Gestisce il filtraggio dei dati per categoria, data e fondo (archivio).
  - **Interazione**: Gestisce click sui cluster (zoom) e sui punti singoli (apertura popup).
  - **Ricerca Similarità**: La funzione `searchSimilarObjects(imageId)` chiama il backend (`POST /search`) per trovare immagini simili a quella selezionata e le visualizza nella sidebar.

- **`grid.js`**:
  - Gestisce una vista alternativa o complementare a "Griglia" (anche se `index.html` sembra focalizzato sulla mappa, questo script gestisce colonne `col-1`...`col-4`).
  - Implementa il **lazy loading** / infinite scroll (`loadMoreFeatures`) per caricare progressivamente gli elementi.
  - Gestisce la visualizzazione dei dettagli nella sidebar al click su un'immagine.

- **`https_server.py`**:
  - Un semplice server web Python (`http.server`) configurato per servire la cartella corrente in **HTTPS**.
  - Utilizza `cert.pem` e `key.pem` per SSL (necessario per alcune feature del browser o per testare in sicurezza locale).
  - Definisce la porta 8080 di default.

### Asset

- **`img/`**: Directory contenente le risorse grafiche (icone per le categorie sulla mappa, immagini di placeholder, ecc.).
