// Grab modal elements
const favoriteModal = document.getElementById('favoriteModal');
// const modalTitle = document.getElementById('modalFeatureTitle');  // You removed it in HTML
const closeBtn = document.getElementById('closeFavoriteModal'); // <— FIXED name

// Function to open modal
async function openFavoriteModal(featureId, event) {
    currentObjectId = featureId; // <-- set the object ID for saving

    if (event) event.stopPropagation();

    let loggedIn = false;
    try {
        const res = await fetch(`${serverURL}/user/status`);
        const data = await res.json();
        loggedIn = data.logged_in;
    } catch (err) {
        console.error("Error checking login status:", err);
    }

    const loginSection = document.getElementById('login-section');
    const collectionSection = document.getElementById('collection-section');

    if (loggedIn) {
        if (loginSection) {
            loginSection.classList.add('hidden');
        }
        if (collectionSection) {
            collectionSection.classList.remove('hidden');
        }
        loadCollections(); // load user's collections
    } else {
        if (loginSection) {
            loginSection.classList.remove('hidden');
        }
        if (collectionSection) {
            collectionSection.classList.add('hidden');
        }
    }

    if (favoriteModal) {
        favoriteModal.classList.remove('hidden');
    }
}



// Function to close modal
function closeFavoriteModal() {
    if (favoriteModal) {
        favoriteModal.classList.add('hidden');
    }
}

// Attach close button
if (closeBtn) {
    closeBtn.addEventListener('click', closeFavoriteModal);
}

// Close on outside click
if (favoriteModal) {
    favoriteModal.addEventListener('click', (e) => {
        if (e.target === favoriteModal) closeFavoriteModal();
    });
}
