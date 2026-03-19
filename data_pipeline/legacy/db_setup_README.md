## Database setup

Questi script servono per inizializzare o aggiornare il database Redis a partire dai file locali.

Attiva prima il virtual environment:

```bash
source ../RADICI/bin/activate
```

Poi esegui gli script dalla cartella `db_setup/`.

```bash
python redis_init.py
```

Importa il contenuto del `.csv` esistente per creare un database Redis pulito.

```bash
python get_new_json_entries.py
```

Legge un file `jsonl` e prepara nuove entry da importare nel database Redis.

```bash
python redis_json_import.py
```

Legge un file `geojson` con coordinate esistenti e aggiorna il database Redis.
