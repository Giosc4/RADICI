let currentObjectId = null;
async function loginUser() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
        alert("Inserisci username e password");
        return;
    }

    try {
        const res = await fetch(`${serverURL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (res.ok) {
            const loginSection = document.getElementById('login-section');
            const collectionSection = document.getElementById('collection-section');

            if (loginSection) {
                loginSection.classList.add('hidden');
            }
            if (collectionSection) {
                collectionSection.classList.remove('hidden');
            }
            loadCollections();  // <-- load collections
            checkUserStatus(); // update header without reload
            alert(data.message);
        } else {
            alert(data.error);
        }
    } catch (err) {
        console.error("Login error:", err);
        alert("Errore durante il login");
    }
}
/*async function loadCollections() {
    const res = await fetch(`${serverURL}/user/collections`, { credentials: 'include' });
    const data = await res.json();
    const select = document.getElementById("collection-select");
    if (!select) {
        return;
    }
    select.innerHTML = "";
    data.collections.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        select.appendChild(opt);
    });
}*/
async function loadCollections() {
    const res = await fetch(`${serverURL}/user/collections`, { credentials: 'include' });
    const data = await res.json();
    const select = document.getElementById("collection-select");
    if (!select) {
        return;
    }
    select.innerHTML = "";

    data.collections.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.name;
        opt.textContent = c.name;

        // 🔥 AUTO-SELECT TARGET COLLECTION
        if (targetCollection && c.name === targetCollection) {
            opt.selected = true;
        }

        select.appendChild(opt);
    });
}

function createCollection() {
    const name = document.getElementById("new-collection-name").value;

    fetch(`${serverURL}/user/collections/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: 'include',   // <— this ensures session cookie is sent
        body: JSON.stringify({ name })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            loadCollections();
        } else {
            alert(data.error || "Failed to create collection");
        }
    });
}

function saveObjectToCollection() {
    const collectionSelect = document.getElementById("collection-select");
    if (!collectionSelect) {
        return;
    }
    const collection = collectionSelect.value;

    fetch(`${serverURL}/user/collections/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: 'include',   // <— important
        body: JSON.stringify({
            object_id: currentObjectId,
            collection_name: collection
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert("Object saved!");
            const loginSection = document.getElementById('login-section');
            const collectionSection = document.getElementById('collection-section');
            const successSection = document.getElementById('success-section');

            if (loginSection) {
                loginSection.classList.add('hidden');
            }
            if (collectionSection) {
                collectionSection.classList.add('hidden');
            }
            if (successSection) {
                successSection.classList.remove('hidden');
                successSection.innerHTML = `
                    <h4>The object has been saved.</h4>
                    <button class="modal-btn primary" onclick="closeFavoriteModal()">Continue browsing</button>
                    <button class="modal-btn" onclick="window.location.href='/sperimentare'">Open collections</button>
                `;
            }
            //closeFavoriteModal();
            //loadFavorites();
        } else {
            alert(data.error || "Error saving object.");
        }
    });
}

// Load current user favorites
async function loadFavorites() {
    try {
        const res = await fetch(`${serverURL}/user/favorites`, {
            credentials: "include"
        });
        const data = await res.json();
        if (!data.favorites) return;

        const favIds = new Set(data.favorites.map(o => o.id));

        document.querySelectorAll(".grid-item").forEach(item => {
            const objId = item.dataset.id;
            const heart = item.querySelector(".heart");
            if (favIds.has(objId)) {
                heart.textContent = "❤️";
                item.classList.add("favorited");
            } else {
                heart.textContent = "♡";
                item.classList.remove("favorited");
            }
        });
    } catch (err) {
        console.error("Failed to load favorites:", err);
    }
}
