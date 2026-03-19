## Docker setup for data pipeline

Questa cartella contiene il Dockerfile e gli script batch per esportare o arricchire il database Redis.

Esegui i comandi da `data_pipeline/docker/`.

Build dell'immagine:

```bash
docker build -t radici-data-pipeline -f Dockerfile ..
```

Esecuzione con mount della repository locale:

```bash
docker run -v /media/data/giacomo.vallasciani/RADICI:/app/data radici-data-pipeline
```

Se il container deve raggiungere Redis o altri servizi sull'host:

```bash
docker run --network host -v /media/data/giacomo.vallasciani/RADICI:/app/data radici-data-pipeline
```
