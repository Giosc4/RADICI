const columns = [
    document.getElementById("col-1"),
    document.getElementById("col-2"),
    document.getElementById("col-3"),
    document.getElementById("col-4")
];

let colIndex = 0;

function clearColumns() {
    columns.forEach(c => c.innerHTML = "");
    colIndex = 0;
}

function renderObject(obj) {
    const item = document.createElement("div");
    item.className = "grid-item";
    item.dataset.id = obj.id;

    const img_file = obj.img_path.split("/").pop();

    item.innerHTML = `
        <img class="grid-item-image" src="${serverURL}/images/${img_file}" alt="${obj.title || ''}">
        <div class="grid-overlay">
            <span>${obj.title || ""}</span>
        </div>
    `;

    columns[colIndex % columns.length].appendChild(item);
    colIndex++;
}

function renderGrid(objects) {
    clearColumns();
    objects.forEach(renderObject);
}

async function loadCollection(collectionName) {
    try {
        const res = await fetch(
            `/api/collection/${encodeURIComponent(collectionName)}`,
            { credentials: "include" }
        );

        const data = await res.json();
        console.log("API response:", data);

        if (!data.success) {
            console.error(data.error);
            return;
        }

        renderGrid(data.objects);
    } catch (err) {
        console.error("Collection load error:", err);
    }
}

// Get collection name from <body data-collection="...">
window.onload = () => {
    const collectionName = document.body.dataset.collection;
    if (collectionName) loadCollection(collectionName);
};
