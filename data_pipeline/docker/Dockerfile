# Use Python 3.11 slim as the base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsm6 libxext6 libxrender-dev \
    libgl1 \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer1.0-dev \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install required Python packages
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    tensorflow \
    opencv-python \
    matplotlib \
    torch \
    torchvision \
    pillow \
    requests \
    redis \
    opencage \
    astunparse

# Copy the current batch scripts into the container
COPY enrich/enrich_redis_entries.py /app/enrich_redis_entries.py
COPY export/export_redis_to_csv_geojson.py /app/export_redis_to_csv_geojson.py
# Set the working directory to /app
WORKDIR /app

# Default command to run the script
#CMD ["python", "enrich_redis_entries.py"]
CMD ["python", "export_redis_to_csv_geojson.py"]
