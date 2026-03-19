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
            document.getElementById('login-section').classList.add('hidden');
            document.getElementById('collection-section').classList.remove('hidden');
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
    const collection = document.getElementById("collection-select").value;

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
            document.getElementById('login-section').classList.add('hidden');
            document.getElementById('collection-section').classList.add('hidden');
            document.getElementById('success-section').classList.remove('hidden');
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
