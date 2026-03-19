const mainContent = document.getElementById('mainContent');

let spinnerStartTime = null;

function showSpinner() {
    spinnerStartTime = Date.now();
    document.getElementById('loading-spinner').classList.remove('hidden');
}

function hideSpinner() {
    const now = Date.now();
    const elapsed = now - spinnerStartTime;
    const minimumDelay = 1000; // 1 second

    const remaining = minimumDelay - elapsed;

    if (remaining > 0) {
        setTimeout(() => {
            document.getElementById('loading-spinner').classList.add('hidden');
        }, remaining);
    } else {
        document.getElementById('loading-spinner').classList.add('hidden');
    }
}


function clearFeatureColumns() {
  ['col-1', 'col-2', 'col-3', 'col-4'].forEach(id => {
      document.getElementById(id).innerHTML = '';
      currentOffset = 0;
  });
}


function parseDateRange(dateStr) {
    if (!dateStr) return null;
  
    // Remove whitespace
    dateStr = dateStr.trim();
  
    // Handle different formats
    if (/^\d{4}$/.test(dateStr)) {
      // Format: "YYYY"
      const year = parseInt(dateStr, 10);
      return { start: year, end: year };
    } else if (/^\d{4}[-/]\d{4}$/.test(dateStr)) {
      // Format: "YYYY-YYYY" or "YYYY/YYYY"
      const parts = dateStr.split(/[-/]/);
      const startYear = parseInt(parts[0], 10);
      const endYear = parseInt(parts[1], 10);
      return { start: startYear, end: endYear };
    } else {
      // Unrecognized format
      return null;
    }
}

function displayFeatures(features) {
    // Clear existing items
    document.querySelectorAll('.feature-item').forEach(item => item.remove());
  
    const columns = [
      document.getElementById('col-1'),
      document.getElementById('col-2'),
      document.getElementById('col-3'),
      document.getElementById('col-4')
    ];
  
    features.forEach((feature, index) => {
      const colIndex = index % columns.length;
      const col = columns[colIndex];
      const img_path = feature.properties.img_path;
      const parts = img_path.split("/");
      const img_file = parts[parts.length - 1];
  
      const itemDiv = document.createElement('div');
      itemDiv.className = 'feature-item image-container-color';
  
      itemDiv.innerHTML = `
      <div class="grid-item">
          <p class="grid-item-title">${feature.properties.title}</p>

          <div class="image-container">
              <img class="grid-item-image"
                  src="${serverURL}/images/${img_file}"
                  alt="${feature.properties.title}"
                  onclick="triggerActions('${feature.properties.id}')">

              <img class="favorite-icon"
                  src = "${ICON_BASE_URL}/signet-icon.png"
                  onclick="openFavoriteModal('${feature.properties.id}', event)"
                  title="Save to collection">
          </div>

          <div class="grid-item-description">
              <p>${feature.properties.description ? feature.properties.description : 'No description available.'}</p>
          </div>
      </div>
      `;
  
      col.appendChild(itemDiv);
    });
  }


//display sidebar on image click
function triggerActions(id) {
    document.getElementById('sidebar_metamotor').style.right = '0';
    document.querySelector('.mainContent').classList.add('blur-background');
    res = getObjectById(id);
    //displayResults(res);
    
    searchSimilarObjects(id);
}

//Function to get 10 random features
function getRandomFeatures(features, count = 10) {
    const shuffled = features.slice().sort(() => 0.5 - Math.random());
    return shuffled.slice(0, count);
}

function loadMoreFeatures() {
  showSpinner();

  setTimeout(() => {
    const nextFeatures = allFeatures.slice(currentOffset, currentOffset + itemsPerPage);

    const columns = [
        document.getElementById('col-1'),
        document.getElementById('col-2'),
        document.getElementById('col-3'),
        document.getElementById('col-4')
    ];

    nextFeatures.forEach((feature, index) => {
        const colIndex = (currentOffset + index) % columns.length;
        const col = columns[colIndex];
        const img_path = feature.properties.img_path;
        const img_file = img_path.split("/").pop();

        const itemDiv = document.createElement('div');
        itemDiv.className = 'feature-item image-container-color';

        itemDiv.innerHTML = `
          <div class="grid-item">
              <p class="grid-item-title">${feature.properties.title}</p>
        
              <div class="image-container">
                  <img class="grid-item-image"
                      src="${serverURL}/images/${img_file}"
                      alt="${feature.properties.title}"
                      onclick="triggerActions('${feature.properties.id}')">
        
                  <img class="favorite-icon"
                      src = "${ICON_BASE_URL}/signet-icon.png"
                      onclick="openFavoriteModal('${feature.properties.id}', event)"
                      title="Save to collection">
              </div>
        
              <div class="grid-item-description">
                  <p>${feature.properties.description ? feature.properties.description : 'No description available.'}</p>
              </div>
          </div>
        `;
      

        col.appendChild(itemDiv);
    });

    currentOffset += itemsPerPage;
    hideSpinner();
  },500);
}

fetch(GEOJSON_URL)//fetch('redis_export.geojson')
  .then(response => response.json())
  .then(geojsonData => {
      allFeatures = getRandomFeatures(geojsonData.features, 100); // or just geojsonData.features if you want them all
      loadMoreFeatures(); // Load the first 20
  })
  .catch(error => console.error('Error loading GeoJSON:', error));


window.addEventListener('scroll', () => {
    const scrollTop = window.scrollY;
    const viewportHeight = window.innerHeight;
    const totalHeight = document.documentElement.scrollHeight;

    // Trigger loading when near the bottom (100px buffer)
    if (scrollTop + viewportHeight >= totalHeight - 100) {
        if (currentOffset < allFeatures.length) {
            loadMoreFeatures();
        }
    }
});
