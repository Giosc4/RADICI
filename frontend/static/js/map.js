const serverHost = window.location.hostname;
const serverPort = '50001';
// const serverURL = `https://${serverHost}:${serverPort}`;
//const serverURL = 'http://137.204.195.17:5030'//'http://137.204.195.17:5030'//`${window.location.protocol}//${window.location.hostname}:${serverPort}`;

const singleTypeIconExpression = (type) => type ? `${type}-icon` : 'default-icon';
const mapboxToken = window.MAPBOX_ACCESS_TOKEN || '';
const mapboxStyle = window.MAPBOX_STYLE_URL || 'mapbox://styles/mapbox/streets-v12';

let keywordIndex = {};
let geojsonData = {};
let currentPopup = null;

function showMapInitError(message) {
    const searchResults = document.getElementById('search-results');
    if (searchResults) {
        searchResults.innerHTML = `<li>${message}</li>`;
    }
}

/*
//Latest addition on 26 september 2025
function applyAllFilters() {
    let filteredFeatures = geojson.features;
    // Build filter array for Mapbox
    const filters = [];
  
    // Type filter
    if (activeFilters.type && activeFilters.type !== 'all') {
      filters.push(['==', ['get', 'type'], activeFilters.type]);
    }
    updateClusterTextField(selectedType);
    // Date filter
    if (activeFilters.date) {
      const dateFilter = ['all'];
      if (activeFilters.date) {
        let filterValue = JSON.parse(activeFilters.date);
        filteredFeatures = filteredFeatures.filter(f => {
            const featureDate = f.properties.date; // your date property
            const dateRangeStr = f.properties.date;
            const dateRange = parseDateRange(dateRangeStr);
            if (dateRange){
                if (dateRange.start >= filterValue.start && dateRange.end <= filterValue.end){
                    dateFilter.push(['==', ['get', 'date'], filterValue.start]);
                }   
            }               
        });  
      }
      filters.push(dateFilter);
    }
  
    // Fondo filter
    if (activeFilters.fondo && activeFilters.fondo !== '') {
      filters.push(['==', ['get', 'fondo'], activeFilters.fondo]);
    }
  
    // Apply combined filter
    const combinedFilter = filters.length > 0 ? ['all', ...filters] : true;
  
    // Set filter on relevant layers
    if (map.getLayer('unclustered-point')) {
        map.setFilter('unclustered-point', combinedFilter);
    }
    if (map.getLayer('clusters')) {
        map.setFilter('clusters', combinedFilter);
    }
    if (map.getLayer('cluster-count')) {
        map.setFilter('cluster-count', combinedFilter);
    }
}*/
function applyAllFilters() {
    let filteredFeatures = geojsonData.features;

    // TYPE
    if (activeFilters.type && activeFilters.type !== 'all') {
        filteredFeatures = filteredFeatures.filter(
            f => f.properties.type === activeFilters.type
        );
    }

    // FONDO
    if (activeFilters.fondo) {
        filteredFeatures = filteredFeatures.filter(
            f => f.properties.fondo === activeFilters.fondo
        );
    }

    // DATE
    if (activeFilters.date) {
        const range = JSON.parse(activeFilters.date);
        filteredFeatures = filteredFeatures.filter(f => {
            const dateRange = parseDateRange(f.properties.date);
            if (!dateRange) return false;
            return (
                dateRange.start >= range.start &&
                dateRange.end <= range.end
            );
        });
    }

    // Update map source
    const source = map.getSource('objects');
    if (source) {
        source.setData({
            type: 'FeatureCollection',
            features: filteredFeatures
        });
    }

    // Update cluster icon count + type icon expression
    updateClusterTextField(activeFilters.type || null);
}


/**
 * Manage the duplicate coordinates and relocate coordinates to avoid overlap
 * @param{json file} geojson — the original geojson file holding coordinates information
 * @param{float} maxOffset — the offset to space the coordinates around the original position
*/
function jitterDuplicateCoordinates(geojson, maxOffset = 0.008){//0.0005) {
    const seen = new Map();
    
    geojson.features.forEach(feature => {
            const coords = feature.geometry.coordinates;
            const key = coords.join(',');
            
            if (seen.has(key)) {
                const count = seen.get(key) + 1;
                seen.set(key, count);
                
                // Random angle and radius (within a circle)
                const angle = Math.random() * 2 * Math.PI;
                const radius = Math.sqrt(Math.random()) * maxOffset; // sqrt for uniform distribution
                
                const dx = Math.cos(angle) * radius;
                const dy = Math.sin(angle) * radius;
                
                feature.geometry.coordinates = [coords[0] + dx, coords[1] + dy];

            } else {
                seen.set(key, 0);
            }
    });
    
    return geojson;
}
    
/**
 * Update the text on top of the cluster icon.
 * The text displays the amount of objects in the cluster
 * @param{string} selectedType — the typology of the objects
*/
function updateClusterTextField(selectedType) {
    if (!map.getLayer('cluster-count')) return;

    const typeToProperty = { 
        publishing: 'publishing_count',
        music: 'music_count',
        architecture: 'architecture_count',
        audiovisual: 'audiovisual_count',
        photography: 'photography_count',
        design: 'design_count',
        mode: 'mode_count',
        dance: 'dance_count'
    };

    const textField = selectedType
        ? ['to-string', ['get', typeToProperty[selectedType]]]
        : ['to-string', ['get', 'point_count']];

    map.setLayoutProperty('cluster-count', 'text-field', textField);
}

/*

function getDateRangeFilter(exp) {
    if (!selectedDateRange) return null; // No filter on date yet
    if (selectedDateRange.includes('..')) { // For a date range (e.g., '2000-2010', '1880/1890')
      // Example parsing, adjust based on your actual date format
      let [from, to] = selectedDateRange.split('..');
      from = new Date(from).getTime();
      to = new Date(to).getTime();
      return ['>=', ['to-number', 'date'], from, '<=', ['to-number', 'date'], to];
    } else if (selectedDateRange.includes('-')) { // Single date or a range with hyphen in format '1905/1915'
      let [start, end] = selectedDateRange.split('-');
      return ['>=', ['to-number', 'date'], new Date(start).getTime(), '<=', ['to-number', 'date'], new Date(end).getTime()];
    } else {
      // If date input is invalid or simple, handle gracefully
      console.warn('Invalid date range format: ' + selectedDateRange);
      return null; // No date filter will be applied if the format is incorrect or missing
    }
  }

  // Example: filtering features based on date range
function filterFeaturesByDate(features, selectedDate) {
    if (!selectedDate) return features;

    const filterValue = JSON.parse(selectedDate); // e.g., {start: '2023-01-01', end: '2023-01-31'}
    return features.filter(f => {
        const dateRangeStr = f.properties.date; // your date property
        const dateRange = parseDateRange(dateRangeStr);
        if (!dateRange) return false;
        return (
            dateRange.start >= filterValue.start &&
            dateRange.end <= filterValue.end
        );
    });
}*/
function updateMapFilters(filteredFeatures, selectedType, selectedFondo = null, selectedDate = null) {
    if (!map.getLayer('unclustered-point') || !map.getLayer('clusters') || !map.getLayer('cluster-count')) {
        return;
    }

    // Step 1: Filter features based on selected filters
    /*const filteredFeatures = geojson.features.filter(feature => {
        const props = feature.properties;
        const matchesType = selectedType ? props.type === selectedType : true;
        const matchesFondo = selectedFondo ? props.fondo === selectedFondo : true;
        const matchesDate = selectedDate ? props.date === selectedDate : true;
        return matchesType && matchesFondo && matchesDate;
    });*/

    // Step 2: Update the source data with filtered features
    const source = map.getSource('objects'); // replace with your actual source ID
    if (source) {
        source.setData({
            type: 'FeatureCollection',
            features: filteredFeatures
        });
    }

    // Step 3: Set filters for unclustered points
    const combinedFilter = (selectedType)
        ? ['==', ['get', 'type'], selectedType]
        : ['!', ['has', 'point_count']];

    map.setFilter('unclustered-point', combinedFilter);

    // Step 4: Set filters for clusters
    const clusterFilter = selectedType
        ? ['>', ['get', `${selectedType}_count`], 0]
        : ['has', 'point_count'];

    map.setFilter('clusters', clusterFilter);
    map.setFilter('cluster-count', clusterFilter);

    // Step 5: Update icon-image based on selectedType
    const iconImageExpr = selectedType
        ? `${selectedType}-icon`
        : generateDominantIconExpression(types); // make sure generateDominantIconExpression is defined

    map.setLayoutProperty('clusters', 'icon-image', iconImageExpr);

    // Step 6: Update icon size based on count
    map.setLayoutProperty('clusters', 'icon-size', [
        'interpolate',
        ['linear'],
        ['get', selectedType ? `${selectedType}_count` : 'point_count'],
        1, 0.2,
        100, 0.3,
        1000, 0.4
    ]);
}
        
/**
 * Generate Mapbox expression to pick the dominant category icon in a cluster
 * @param {string[]} types - Array of category type strings
 * @returns {Array} Mapbox 'case' expression
 */
function generateDominantIconExpression(types) {
    const expression = ['case'];

    for (let i = 0; i < types.length; i++) {
        const current = types[i];
        const others = types.filter(t => t !== current);
        const maxExpression = ['max', ...others.map(t => ['get', `${t}_count`])];

        expression.push(['>', ['get', `${current}_count`], maxExpression]);
        expression.push(`${current}-icon`);
    }

    expression.push('default-icon'); // fallback
    return expression;
}

/**
 * Filter objects based on type
 * @param {string} types — the select type based on established typology to classify objects
 * @param {string} layer_id — the id of the layer holding corresponding objects for the given type
*/
function createTypeFilterUI(types, layer_id) {
    const container = document.getElementById('type-filter');
    if (!container) {
        return;
    }
    container.innerHTML = ''; // Clear existing buttons

    let selectedType = 'all';

    const iconContainer = document.createElement('div');
    iconContainer.className = 'icon-column';

    const createIcon = (type, label) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'type-icon';
        wrapper.dataset.type = type;

        if (type === 'all') {
            wrapper.classList.add('all');
            //wrapper.textContent = 'All';
            const labelDiv = document.createElement('div');
            labelDiv.className = 'label';
            labelDiv.textContent = 'All';
            wrapper.appendChild(labelDiv);
        } else {
            const icon = document.createElement('div');
            icon.innerHTML = `<img src="${ICON_BASE_URL}/icons/${type}-icon.svg" alt="${label}" style="width: 24px;">`;
            wrapper.appendChild(icon);

            const labelDiv = document.createElement('div');
            labelDiv.className = 'label';
            labelDiv.textContent = label;
            wrapper.appendChild(labelDiv);
        }

        if (type === selectedType) {
            wrapper.classList.add('selected');
        }

        wrapper.addEventListener('click', () => {
            selectedType = type;
            document.querySelectorAll('.type-icon').forEach(el => {
                el.classList.remove('selected');
            });
            wrapper.classList.add('selected');
            //updateMapFilters(type === 'all' ? null : type);


            //THIS IS TO APPLY THE FILTER ON THE GRID AS WELL
            

            if (type == 'all'){
                activeFilters['type'] = null;
            }else{
                activeFilters['type'] = type;
            }
            // Update button UI: mark only this button as selected in its category
            updateButtonSelections('type', type);
            // Apply filters
            filterFeatures();
        });

        return wrapper;
    };

    iconContainer.appendChild(createIcon('all', 'All'));
    types.forEach(type => {
        iconContainer.appendChild(createIcon(type, type));
    });

    const backgroundWrapper = document.createElement('div');
    backgroundWrapper.id = 'type-filter-wrapper';
    backgroundWrapper.appendChild(iconContainer);

    container.appendChild(backgroundWrapper);

    // Set default filter
    //updateMapFilters(null);
}

/**
 * Setup the URL to reach the original archive
 * @param {string} archive — the name of the archive
 * @param {string} id — the id of the image
*/
function setupURL(archive, id){
    switch (archive) {
        case "lodovico": return `https://lodovico.medialibrary.it/media/schedadl.aspx?id=${id}`
        case "classense": return `https://www.cdc.classense.ra.it/s/Classense/item/${id}`
        default: return `http://www.ilcorago.org/benedetti/scheda.asp?id_disco=%27${id}%27`;//feature.properties.url;
    }
}

/*
    * Display similar images in the different archives used
    * @param {string} imageId — The id of the select image
*/
async function searchSimilarObjects(imageId) {
    const similarItems = document.getElementById('similar-items');
    if (similarItems) {
        similarItems.innerHTML = 'Loading...';
    }
    try {
        const response = await fetch(`${serverURL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_id: imageId })
        });
        if (!response.ok) throw new Error('Request failed');

        const results = await response.json();
        displayResults(results); // your existing display function
    } catch (error) {
        console.error(error);
        const similarItems = document.getElementById('similar-items');
        if (similarItems) {
            similarItems.innerHTML = 'Nessun oggetto simile è stato trovato.';
        }
    }
}

/**
 * Display Popup for points
*/
function displayPopup(feature, map){
    const coordinates = feature.geometry.coordinates.slice();
    const date = feature.properties.date;
    const title = feature.properties.title;
    const author = feature.properties.author;
    const place = feature.properties.place;
    const archive = feature.properties.archive;
    const description = feature.properties.description;
    const img_path = feature.properties.img_path;

    const id = feature.properties.id;

    const url = setupURL(archive, id)

    //Lodovico https://lodovico.medialibrary.it/media/schedadl.aspx?id=15108e57-8688-43a2-b760-871749b5ea97
    //Classense https://www.cdc.classense.ra.it/s/Classense/item/{id}

    // Split by "/" and get the last part
    const parts = img_path.split("/");
    const img_file = parts[parts.length - 1];   

    // Ensure that if the map is zoomed out such that
    // multiple copies of the feature are visible, the
    // popup appears over the copy being pointed to.
    if (['mercator', 'equirectangular'].includes(map.getProjection().name)) {
        while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
            coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
        }
    }

    const imageId = feature.properties.id;  // make sure your GeoJSON has this field
    // Close existing popup if any
    if (currentPopup) {
        currentPopup.remove();
    }
    //http://130.136.2.161:8080
    currentPopup = new mapboxgl.Popup({ className: 'custom-popup' })
        .setLngLat(coordinates)
        .setHTML(`
            <div class="popup-content">
                <div class="image-container-popup">
                    <img id="objectImage" src="${serverURL}/images/${img_file}" alt="${title}" />
                </div>
                <div class="popup-title">
                    <span>${title}</span>
                    <img src="${ICON_BASE_URL}/arrow.svg" class="popup-arrow" alt="toggle arrow" />
                </div>
                <div class="popup-short-text">${description}</div>
                <button class="popup-espandi-btn">Espandi</button>
            </div>
        `
        )
        .addTo(map);

    setTimeout(() => {
        const popupEl = document.querySelector('.mapboxgl-popup.custom-popup');
        const mainContent = document.getElementById('main-content');

        if (popupEl) {
            const titleToggle = popupEl.querySelector('.popup-title');
            const shortText = popupEl.querySelector('.popup-short-text');
            const expandButton = popupEl.querySelector('.popup-espandi-btn');

            if (titleToggle && shortText) {
                titleToggle.addEventListener('click', () => {
                    const isVisible = shortText.style.display === 'block';
                    shortText.style.display = isVisible ? 'none' : 'block';
                    titleToggle.classList.toggle('expanded', !isVisible);
                });
            }

            if (expandButton) {
                expandButton.addEventListener('click', () => {
                    const sidebar = document.getElementById('sidebar_metamotor');
                    const mainContent = document.querySelector('.mainContent');
                    if (sidebar) {
                        sidebar.style.right = '0';
                    }
                    if (mainContent) {
                        mainContent.classList.add('blur-background');
                    }
                    console.log("Search similar objects");
                    console.log(id);
                    searchSimilarObjects(id);
                });
            }
        }
    }, 100);

    
    const sidebar = document.getElementById('sidebar_metamotor');
    const mainContent = document.getElementById('main-content');
}
let map;
function initMap(geojson) {
if (!mapboxToken) {
    showMapInitError('Mappa non disponibile: MAPBOX_ACCESS_TOKEN mancante.');
    return;
}

mapboxgl.accessToken = mapboxToken;

map = new mapboxgl.Map({
    container: 'map-canvas',
    // Choose from Mapbox's core styles, or make your own style with Mapbox Studio
    style: mapboxStyle,
    center: [11.327591, 44.498955],
    zoom: 7.2
});

map.on('error', (event) => {
    const message = (event && event.error && event.error.message) ? event.error.message : '';
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('access token') || lowerMessage.includes('unauthorized')) {
        showMapInitError('Mappa non disponibile: token o stile Mapbox non autorizzati (errore 401).');
    }
});

/* ORIGINAL TYPOLOGY
    written document = "elaborati tecnici, Documento archivistico, libri e opuscoli, periodici,"
    photography = "forografie, Fotografia"
    painting = "affresco, dipinto, Affresco, Dipinto"
    audio = "fonti audioali"
    drawing = "disegni e incisioni, Disegno, Disegno di architettura, Cartolina"
    print = "Stampa, documenti a stampa, Ritaglio di stampa"
    scultpure = "Scultura, Elemento architettonico"
    manuscript = "documenti manoscritti, volumi manoscritti"
    map = "Cartografia manoscritta, mappe"
    object = "oggetti museali, opere d'arte, unità archivistiche, nan"
*/
map.on('load', async () => {

    src = ""
    map.loadImage(`${ICON_BASE_URL}/icons-png/default-icon.png`, (error, image) => {
        if (error) throw error;
        if (!map.hasImage('default-icon')) {
        map.addImage('default-icon', image);
        }
    });
    // Load your GeoJSON
    // const response = await fetch('objects_types_and_coordinates.geojson');
    // const data = await response.json();
    const response = await fetch(GEOJSON_URL)//fetch('redis_export.geojson')//'objects_and_coordinates_18_09_2025.geojson')
    const rawGeoJSON = await response.json();
    
    const data = jitterDuplicateCoordinates(rawGeoJSON);
    geojsonData = data;
    //buildKeywordIndex(geojsonData);

    types.forEach(type => {
        const iconPath = `${ICON_BASE_URL}/icons-png/${type}-icon.png`
        //const iconPath = `img/icons-png/${type}-icon.png`; // Adjust path as needed
        map.loadImage(iconPath, (error, image) => {
            if (error) {
                console.error(`Error loading image for ${type}:`, error);
                return;
            }
            if (!map.hasImage(`${type}-icon`)) {
                map.addImage(`${type}-icon`, image);
            }
        });
    });
        
    // Add a new source from our GeoJSON data and
    // set the 'cluster' option to true. GL-JS will
    // add the point_count property to your source data.
    map.addSource('objects', {
        type: 'geojson',
        data: data,
        cluster: true,
        clusterMaxZoom: 14, // Max zoom to cluster points on
        clusterRadius: 50, // Radius of each cluster when clustering points (defaults to 50)
        clusterProperties: {
            publishing_count: ["+", ["case", ["==", ["get", "type"], "publishing"], 1, 0]],
            music_count: ["+", ["case", ["==", ["get", "type"], "music"], 1, 0]],
            architecture_count: ["+", ["case", ["==", ["get", "type"], "architecture"], 1, 0]],
            audiovisual_count: ["+", ["case", ["==", ["get", "type"], "audiovisual"], 1, 0]],
            photography_count: ["+", ["case", ["==", ["get", "type"], "photography"], 1, 0]],
            design_count: ["+", ["case", ["==", ["get", "type"], "design"], 1, 0]],
            mode_count: ["+", ["case", ["==", ["get", "type"], "mode"], 1, 0]], 
            dance_count: ["+", ["case", ["==", ["get", "type"], "dance"], 1, 0]]
        }
    });

    map.addLayer({
        id: 'clusters',
        type: 'symbol',
        source: 'objects',
        filter: ['has', 'point_count'],
        layout: {
            'icon-image': generateDominantIconExpression(types),
            'icon-size': [
                'interpolate',
                ['linear'],
                ['get', 'point_count'],
                1, 0.3,
                100, 0.4,
                1000, 0.5
                //1, 0.01,
                //100, 0.05,
                //1000, 0.09
            ],
            'icon-allow-overlap': true
        }
    });

    map.addLayer({
        id: 'cluster-count',
        type: 'symbol',
        source: 'objects',
        filter: ['has', 'point_count'],
        layout: {
            'text-field': ['get', 'point_count_abbreviated'],
            'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
            'text-size': 12
        },
        paint: {
            "text-color": "#fff"
        }
    });

    map.addLayer({
        id: 'unclustered-point',
        type: 'symbol',
        source: 'objects',
        filter: ['!', ['has', 'point_count']],
        layout: {
            'icon-image': ['concat', ['get', 'type'], '-icon'],
            'icon-size': 0.2,//0.05,
            'icon-allow-overlap': true
        }
    });

    // inspect a cluster on click
    map.on('click', 'clusters', (e) => {
        const features = map.queryRenderedFeatures(e.point, {
            layers: ['clusters']
        });
        const clusterId = features[0].properties.cluster_id;
        map.getSource('objects').getClusterExpansionZoom(
            clusterId,
            (err, zoom) => {
                if (err) return;

                map.easeTo({
                    center: features[0].geometry.coordinates,
                    zoom: zoom
                });
            }
        );
    });

    // When a click event occurs on a feature in
    // the unclustered-point layer, open a popup at
    // the location of the feature, with
    // description HTML from its properties.
    map.on('click', 'unclustered-point', (e) => {
        const feature = e.features[0];
        displayPopup(feature, map); 
    });

    map.on('mouseenter', 'clusters', () => {
        map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'clusters', () => {
        map.getCanvas().style.cursor = '';
    });
    map.on('mouseenter', 'unclustered-point', () => {
        map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'unclustered-point', () => {
        map.getCanvas().style.cursor = '';
    });

    // Create UI controls
    createTypeFilterUI(types, 'unclustered-point');
});
}
