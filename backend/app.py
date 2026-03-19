# app_redis.py

import sys
from flask import Flask, request, jsonify, send_from_directory, Response
from flask import session, redirect, url_for, render_template, render_template_string, jsonify
from flask_cors import CORS
import numpy as np
import redis
import json
import os
import re
import faiss
import nltk
import hashlib
import datetime
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import defaultdict
from sentence_transformers import SentenceTransformer
from datetime import timedelta

import numpy.core.numeric as numeric
sys.modules['numpy._core.numeric'] = numeric

# Paths are resolved from the repository root so the backend can serve the
# integrated frontend directly, without relying on a separate frontend server.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
FRONTEND_TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
FRONTEND_STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

def load_env_file(env_path, override=False):
    """Load simple KEY=VALUE pairs from a local .env file without extra deps."""
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and (override or key not in os.environ):
                os.environ[key] = value

# Load the shared environment first and then apply machine-specific overrides.
# This allows `.env.local` to change local ports, Redis endpoints, or other
# developer-specific settings without modifying the base configuration.
load_env_file(os.path.join(PROJECT_ROOT, ".env"))
load_env_file(os.path.join(PROJECT_ROOT, ".env.local"), override=True)

# ---------------------------------------------------------
# Redis + Flask Setup
# ---------------------------------------------------------
# DB 10 stores cultural objects and their metadata.
# DB 12 stores users, collections, and application-specific account state.
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB_OBJECTS = int(os.environ.get("REDIS_DB_OBJECTS", "10"))
REDIS_DB_USERS = int(os.environ.get("REDIS_DB_USERS", "12"))

# The same Flask process serves both API routes and the integrated frontend.
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_OBJECTS, decode_responses=True)
r_users = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_USERS, decode_responses=True)
app = Flask(
    __name__,
    template_folder=FRONTEND_TEMPLATES_DIR,
    static_folder=FRONTEND_STATIC_DIR,
    static_url_path="/static"
)
# CORS(app, supports_credentials=True, origins=["http://localhost:8000"])

# app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change_this_secret")  # session secret
# app.permanent_session_lifetime = datetime.timedelta(days=7)  # optional: session lifetime

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "secret_key")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['MAPBOX_ACCESS_TOKEN'] = os.environ.get("MAPBOX_ACCESS_TOKEN", "")
app.config['MAPBOX_STYLE_URL'] = os.environ.get("MAPBOX_STYLE_URL", "mapbox://styles/mapbox/streets-v12")

# REQUIRED for cookies to work CROSS-ORIGIN
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"},
    SESSION_COOKIE_HTTPONLY=True
)

CORS(
    app,
    supports_credentials=True,
    resources={r"/*": {"origins": [
        # 8080 is now the default public-facing port for the integrated stack.
        # 5030 is kept temporarily for compatibility with older local setups.
        "http://localhost:8080",
        "https://localhost:8080",
        "http://localhost:5030",
        "https://localhost:5030",
        "http://localhost:8000",
        "http://192.168.249.170:8000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "https://127.0.0.1:8080",
        "http://127.0.0.1:5030",
        "https://127.0.0.1:5030"
    ]}}
)

MODEL_NAME = os.environ.get("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
MODEL = None
MODEL_LOAD_ERROR = None

def get_model():
    """Lazily load the sentence-transformer model from local files only."""
    global MODEL, MODEL_LOAD_ERROR

    if MODEL is not None:
        return MODEL

    if MODEL_LOAD_ERROR is not None:
        return None

    try:
        MODEL = SentenceTransformer(MODEL_NAME, local_files_only=True)
    except Exception as exc:
        MODEL_LOAD_ERROR = str(exc)
        print(f"Warning: sentence-transformer model unavailable offline: {MODEL_LOAD_ERROR}")
        return None

    return MODEL

# Default object schema used when a new record is created from the UI.
# Keeping a complete field set avoids partial records and simplifies
# frontend assumptions about which keys always exist.
DEFAULT_FIELDS = {
    "image": "",
    "url": "",
    "tags": "",
    "model_base": "",
    "place": "",
    "date": "",
    "fondo": "",
    "coordinates": "[]",
    "img_path": "",
    "type": "",
    "archive": "",
    "origin": "",
    "embeddings": "",
    "title": "",
    "id": "",
    "singer": "",
    "author": "",
    "model_lora": ""
}

DEFAULT_IMAGES_DIR = os.path.join(PROJECT_ROOT, "backend", "downloaded_images")
LEGACY_IMAGES_DIR = "/home/valentine.bernasconi/RADICI/downloaded_images"
# Prefer the current repository layout, but keep a fallback for older
# environments where images may still live in a historical absolute path.
IMAGES_DIR = os.environ.get(
    "IMAGES_DIR",
    DEFAULT_IMAGES_DIR if os.path.isdir(DEFAULT_IMAGES_DIR) else LEGACY_IMAGES_DIR
)
print(IMAGES_DIR)

# ---------------------------------------------------------
# NLP Setup
# ---------------------------------------------------------
PUNKT_AVAILABLE = True
STOPWORDS_AVAILABLE = True

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    PUNKT_AVAILABLE = False
    print("Warning: NLTK punkt tokenizer not available locally. Falling back to regex tokenization.")

try:
    stop_words = set(stopwords.words('english') + stopwords.words('italian'))
except LookupError:
    STOPWORDS_AVAILABLE = False
    stop_words = set()
    print("Warning: NLTK stopwords corpus not available locally. Continuing with an empty stopword set.")

import re

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def get_next_object_id():
    keys = r.keys("*")  # all keys
    numeric_keys = [int(k) for k in keys if k.isdigit()]  # only numeric keys
    if not numeric_keys:
        return 1
    return max(numeric_keys) + 1

def extract_keywords(text):
    """Extract sanitized keywords from a text."""
    if not text:
        return []

    text = re.sub(r"[^\w\s]", " ", text.lower())
    if PUNKT_AVAILABLE:
        tokens = word_tokenize(text)
    else:
        tokens = re.findall(r"\b\w+\b", text)

    keywords = [t for t in tokens if t not in stop_words and len(t) > 2]
    return keywords

# ---------------------------------------------------------
# Load FAISS index from Redis hashes
# ---------------------------------------------------------
def load_faiss_from_redis():
    """Build the in-memory FAISS index used for similarity search."""
    keys = r.keys("*")
    objects = []
    embeddings = []

    for key in keys:
        obj = r.hgetall(key)
        if not obj:
            continue
        emb = obj.get("embeddings")
        if not emb:
            continue

        emb = np.array(json.loads(emb), dtype=np.float32)
        embeddings.append(emb)
        objects.append(obj)

    dim = 384  # embedding dimension of all-MiniLM-L6-v2
    if len(embeddings) == 0:
        return [], faiss.IndexFlatL2(dim)

    embeddings = np.vstack(embeddings).astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    return objects, index


def load_keyword_index_from_redis():
    """Build the keyword lookup structures and optional FAISS keyword index."""
    model = get_model()
    if model is None:
        dim = 384
        return {}, [], np.zeros((0, dim), dtype="float32"), faiss.IndexFlatL2(dim)

    keys = r.keys("*")
    keyword_map = defaultdict(list)
    keyword_list = []

    for key in keys:

        # Skip the cache
        if key == "place_coordinates_cache":
            continue

        obj = r.hgetall(key)
        if not obj:
            continue
        #obj_id = obj["id"]  # keep as string
        obj_id = obj.get("id")
        if not obj_id:
            continue  # skip entries without an id


        text = " ".join([
            obj.get("title", ""),
            obj.get("description", ""),
            obj.get("author", ""),
            obj.get("origin", ""),
            obj.get("model_base", ""),
            obj.get("singer", "")
        ])

        kws = extract_keywords(text)
        for kw in kws:
            if kw not in keyword_map:
                keyword_list.append(kw)
            keyword_map[kw].append(obj_id)

    if len(keyword_list) == 0:
        dim = 384
        return {}, [], np.zeros((0, dim), dtype="float32"), faiss.IndexFlatL2(dim)

    keyword_embeddings = model.encode(keyword_list).astype("float32")
    keyword_faiss = faiss.IndexFlatL2(keyword_embeddings.shape[1])
    keyword_faiss.add(keyword_embeddings)

    return keyword_map, keyword_list, keyword_embeddings, keyword_faiss


def refresh_runtime_indexes():
    """Rebuild in-memory search structures after Redis object mutations."""
    global redis_objects, redis_faiss, keyword_map, keyword_list, keyword_embeddings, keyword_faiss

    redis_objects, redis_faiss = load_faiss_from_redis()
    keyword_map, keyword_list, keyword_embeddings, keyword_faiss = load_keyword_index_from_redis()


def list_object_records(limit=500, query=""):
    """Return object-like records from DB10, skipping helper/cache keys."""
    records = []
    query_lower = query.lower().strip()

    for key in r.scan_iter():
        if key == "place_coordinates_cache":
            continue

        if r.type(key) != "hash":
            continue

        obj = r.hgetall(key)
        if not obj:
            continue

        obj_id = obj.get("id", key)
        title = obj.get("title", "")
        archive = obj.get("archive", "")
        type_ = obj.get("type", "")
        searchable = " ".join([obj_id, title, archive, type_]).lower()

        if query_lower and query_lower not in searchable:
            continue

        records.append({
            "redis_key": key,
            "id": obj_id,
            "title": title,
            "archive": archive,
            "type": type_,
            "image": obj.get("image", ""),
            "date": obj.get("date", "")
        })

    def sort_key(item):
        item_id = item.get("id", "")
        return (0, int(item_id)) if item_id.isdigit() else (1, item_id.lower())

    records.sort(key=sort_key)
    return records[:limit]

print("Loading Redis FAISS embeddings…")
redis_objects, redis_faiss = load_faiss_from_redis()

print("Loading keyword FAISS index…")
keyword_map, keyword_list, keyword_embeddings, keyword_faiss = load_keyword_index_from_redis()

# ---------------------------------------------------------
# UPLOAD IMAGES
# ---------------------------------------------------------
@app.route("/upload_image", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    img = request.files["image"]
    filename = img.filename

    save_path = os.path.join(IMAGES_DIR, filename)
    img.save(save_path)

    # Frontend will store this directly into Redis
    return jsonify({
        "filename": filename,
        "img_path": f"/images/{filename}"
    }), 200

@app.route("/add_object", methods=["POST"])
@login_required
def add_object():
    global keyword_map, keyword_list, keyword_embeddings, keyword_faiss
    model = get_model()

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Assign numeric ID
    obj_id = str(get_next_object_id())

    # Full container path for the image
    filename = data.get("img_path", "").replace("/images/", "")
    full_img_path = f"/images/{filename}" if filename else "/images/default.jpeg"


    # ----------------------------
    # FIELD MAPPING (frontend → Redis)
    # ----------------------------
    mapped = {
        "id": obj_id,
        "title": data.get("title", ""),
        "model_base": data.get("description", ""),     # description → model_base
        "author": data.get("author", ""),
        "singer": data.get("singer", ""),
        "date": data.get("date", ""),
        "fondo": data.get("fondo", ""),
        "archive": data.get("archive", ""),
        "place": data.get("place", ""),
        "type": data.get("type", ""),
        "origin": data.get("origin", ""),
        "url": data.get("url", ""),
        "model_lora": data.get("model_lora", ""),
        "coordinates": json.dumps(data.get("coordinates", [])),
        "tags": json.dumps(data.get("tags", [])),
        "img_path": full_img_path,
        "image": filename,  # keep just the filename
        "embeddings": ""  # FILLED LATER BY YOUR EMBEDDING PIPELINE
    }

    # --------------------------------
    # Save object into Redis
    # --------------------------------
    r.hset(obj_id, mapping=mapped)

    # --------------------------------
    # Build text for keyword index
    # --------------------------------
    text = " ".join([
        mapped["title"],
        mapped["model_base"],
        mapped["author"],
        mapped["place"],
        mapped["origin"],
        mapped["singer"],
        mapped["type"]
    ])

    # Extract keywords
    new_keywords = extract_keywords(text)

    # --------------------------------
    # Update keyword FAISS index
    # --------------------------------
    for kw in new_keywords:
        if kw not in keyword_map:
            keyword_map[kw] = []
            keyword_list.append(kw)

            if model is None:
                continue

            kw_emb = model.encode([kw]).astype(np.float32)

            if keyword_embeddings is None or len(keyword_embeddings) == 0:
                keyword_embeddings = kw_emb
                keyword_faiss = faiss.IndexFlatL2(kw_emb.shape[1])
                keyword_faiss.add(kw_emb)
            else:
                keyword_embeddings = np.vstack([keyword_embeddings, kw_emb])
                keyword_faiss.add(kw_emb)

        keyword_map[kw].append(obj_id)

    refresh_runtime_indexes()

    return jsonify({
        "object_id": obj_id,
        "added_keywords": new_keywords
    }), 201

# ---------------------------------------------------------
# HANDLE ROUTES
# ---------------------------------------------------------
@app.route("/")
@app.route("/esplorare")
def esplorare():
    return render_template("grid.html")

@app.route("/documentarsi")
def documentarsi():
    return render_template("documentarsi.html")

@app.route("/sperimentare")
def sperimentare():
    return render_template("sperimentare.html")

@app.route("/about")
def about():
    return render_template("about.html")

ADMIN_REDIS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>Redis Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body { margin: 0; font-family: 'Martian Mono', monospace; background: #f7f1eb; color: #372215; }
        .page { padding: 32px; }
        .layout { display: grid; grid-template-columns: minmax(320px, 420px) minmax(420px, 1fr); gap: 24px; align-items: start; }
        .card { border: 1px solid #d8c4b6; background: #fffaf6; padding: 18px; }
        .title { font-size: 1.4rem; margin-bottom: 8px; }
        .subtitle { font-size: 0.9rem; opacity: 0.8; margin-bottom: 18px; }
        .toolbar, .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
        .input, .textarea, .button { font: inherit; }
        .input, .textarea { width: 100%; border: 1px solid #cdb19f; background: white; padding: 10px 12px; }
        .textarea { min-height: 520px; resize: vertical; font-family: monospace; font-size: 0.9rem; line-height: 1.4; }
        .button { border: 1px solid #372215; background: white; color: #372215; padding: 8px 12px; cursor: pointer; }
        .button.primary { background: #372215; color: white; }
        .list { max-height: 70vh; overflow: auto; border-top: 1px solid #ead8cc; }
        .item { border-bottom: 1px solid #ead8cc; padding: 12px 0; cursor: pointer; }
        .item.active { background: #f4e8df; }
        .meta { font-size: 0.85rem; opacity: 0.8; }
        .status { min-height: 24px; font-size: 0.9rem; margin-bottom: 12px; }
        .summary { margin-bottom: 16px; padding: 12px; background: #f4e8df; border: 1px solid #e1ccbf; }
        .summary strong { display: inline-block; min-width: 160px; }
        @media (max-width: 980px) { .layout { grid-template-columns: 1fr; } .textarea { min-height: 360px; } }
    </style>
</head>
<body>
    <div class="page">
        <div class="layout">
            <section class="card">
                <div class="title">Redis Admin</div>
                <div class="subtitle">Browse and manage object records currently stored in Redis DB 10. This page is intended for trusted editors only.</div>
                <div id="redis-summary" class="summary">Loading Redis summary...</div>
                <div class="toolbar">
                    <input id="record-search" class="input" type="text" placeholder="Search by id, title, archive, type">
                    <button id="refresh-records" class="button">Refresh</button>
                    <button id="new-record" class="button">New Record</button>
                </div>
                <div id="record-count" class="subtitle"></div>
                <div id="record-list" class="list"></div>
            </section>
            <section class="card">
                <div class="title">Record Editor</div>
                <div class="subtitle">Edit the selected Redis hash as JSON. Save to update or create, delete to remove the current record.</div>
                <div id="admin-status" class="status"></div>
                <div class="toolbar">
                    <input id="record-id" class="input" type="text" placeholder="Redis record id">
                </div>
                <textarea id="record-json" class="textarea" spellcheck="false"></textarea>
                <div class="actions">
                    <button id="save-record" class="button primary">Save</button>
                    <button id="delete-record" class="button">Delete</button>
                </div>
            </section>
        </div>
    </div>
    <script>
        const serverURL = window.location.origin;
        const recordListEl = document.getElementById('record-list');
        const recordSearchEl = document.getElementById('record-search');
        const recordCountEl = document.getElementById('record-count');
        const recordIdEl = document.getElementById('record-id');
        const recordJsonEl = document.getElementById('record-json');
        const adminStatusEl = document.getElementById('admin-status');
        const redisSummaryEl = document.getElementById('redis-summary');
        let selectedRecordId = null;

        function setStatus(message, isError = false) {
            adminStatusEl.textContent = message || '';
            adminStatusEl.style.color = isError ? '#a12626' : '#372215';
        }

        async function loadSummary() {
            const res = await fetch(`${serverURL}/admin/api/redis/summary`, { credentials: 'include' });
            const data = await res.json();
            if (!data.success) {
                redisSummaryEl.textContent = data.error || 'Failed to load Redis summary';
                return;
            }
            redisSummaryEl.innerHTML = `
                <div><strong>Objects DB (${data.summary.object_db}):</strong> ${data.summary.object_count} keys</div>
                <div><strong>Users DB (${data.summary.user_db}):</strong> ${data.summary.user_count} keys</div>
                <div><strong>Search indexes:</strong> ${data.summary.loaded_object_count} objects loaded in memory</div>
            `;
        }

        function prettyRecord(record = {}) {
            return JSON.stringify(record, null, 2);
        }

        async function loadRecords() {
            const q = recordSearchEl.value.trim();
            const res = await fetch(`${serverURL}/admin/api/redis/records?q=${encodeURIComponent(q)}`, { credentials: 'include' });
            const data = await res.json();
            if (!data.success) {
                setStatus(data.error || 'Failed to load records', true);
                return;
            }
            recordCountEl.textContent = `${data.records.length} records loaded`;
            recordListEl.innerHTML = '';
            data.records.forEach((record) => {
                const item = document.createElement('div');
                item.className = 'item';
                if (record.redis_key === selectedRecordId) item.classList.add('active');
                item.innerHTML = `<div><strong>${record.id}</strong> ${record.title ? `- ${record.title}` : ''}</div><div class="meta">${record.archive || '-'} | ${record.type || '-'} | ${record.date || '-'}</div>`;
                item.addEventListener('click', () => loadRecord(record.redis_key));
                recordListEl.appendChild(item);
            });
        }

        async function loadRecord(recordId) {
            const res = await fetch(`${serverURL}/admin/api/redis/records/${encodeURIComponent(recordId)}`, { credentials: 'include' });
            const data = await res.json();
            if (!data.success) {
                setStatus(data.error || 'Failed to load record', true);
                return;
            }
            selectedRecordId = data.redis_key;
            recordIdEl.value = data.record.id || data.redis_key;
            recordJsonEl.value = prettyRecord(data.record);
            setStatus(`Loaded record ${data.redis_key}`);
            loadRecords();
        }

        function newRecord() {
            selectedRecordId = null;
            recordIdEl.value = '';
            recordJsonEl.value = prettyRecord({
                title: "", model_base: "", author: "", singer: "", date: "", fondo: "",
                archive: "", place: "", type: "", origin: "", url: "", model_lora: "",
                coordinates: "[]", tags: "[]", img_path: "/images/default.jpeg", image: "", embeddings: ""
            });
            setStatus('Creating a new record');
            loadRecords();
        }

        async function saveRecord() {
            let parsed;
            try {
                parsed = JSON.parse(recordJsonEl.value);
            } catch (err) {
                setStatus(`Invalid JSON: ${err.message}`, true);
                return;
            }
            const explicitId = recordIdEl.value.trim();
            if (explicitId) parsed.id = explicitId;
            const targetId = explicitId || selectedRecordId;
            const isUpdate = Boolean(targetId);
            const url = isUpdate ? `${serverURL}/admin/api/redis/records/${encodeURIComponent(targetId)}` : `${serverURL}/admin/api/redis/records`;
            const method = isUpdate ? 'PUT' : 'POST';
            const res = await fetch(url, {
                method,
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record: parsed })
            });
            const data = await res.json();
            if (!data.success) {
                setStatus(data.error || 'Save failed', true);
                return;
            }
            selectedRecordId = data.id;
            setStatus(data.message || 'Saved');
            await loadSummary();
            await loadRecord(data.id);
        }

        async function deleteRecord() {
            const targetId = recordIdEl.value.trim() || selectedRecordId;
            if (!targetId) {
                setStatus('No record selected', true);
                return;
            }
            if (!window.confirm(`Delete record ${targetId}?`)) return;
            const res = await fetch(`${serverURL}/admin/api/redis/records/${encodeURIComponent(targetId)}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            const data = await res.json();
            if (!data.success) {
                setStatus(data.error || 'Delete failed', true);
                return;
            }
            selectedRecordId = null;
            recordIdEl.value = '';
            recordJsonEl.value = '';
            setStatus(data.message || 'Deleted');
            loadSummary();
            loadRecords();
        }

        document.getElementById('refresh-records').addEventListener('click', loadRecords);
        document.getElementById('new-record').addEventListener('click', newRecord);
        document.getElementById('save-record').addEventListener('click', saveRecord);
        document.getElementById('delete-record').addEventListener('click', deleteRecord);
        recordSearchEl.addEventListener('keyup', (event) => { if (event.key === 'Enter') loadRecords(); });
        window.addEventListener('load', async () => {
            await loadSummary();
            await loadRecords();
        });
    </script>
</body>
</html>
"""


@app.route("/admin/redis")
@login_required
def admin_redis():
    return render_template_string(ADMIN_REDIS_TEMPLATE)


@app.route("/admin/api/redis/summary", methods=["GET"])
@login_required
def admin_redis_summary():
    return jsonify({
        "success": True,
        "summary": {
            "object_db": REDIS_DB_OBJECTS,
            "object_count": r.dbsize(),
            "user_db": REDIS_DB_USERS,
            "user_count": r_users.dbsize(),
            "loaded_object_count": len(redis_objects)
        }
    })


@app.route("/admin/api/redis/records", methods=["GET"])
@login_required
def admin_list_redis_records():
    limit = request.args.get("limit", default=200, type=int)
    limit = max(1, min(limit, 1000))
    query = request.args.get("q", default="", type=str)

    return jsonify({
        "success": True,
        "records": list_object_records(limit=limit, query=query)
    })


@app.route("/admin/api/redis/records/<record_id>", methods=["GET"])
@login_required
def admin_get_redis_record(record_id):
    obj = r.hgetall(record_id)
    if not obj:
        return jsonify({"success": False, "error": "Record not found"}), 404

    return jsonify({"success": True, "record": obj, "redis_key": record_id})


@app.route("/admin/api/redis/records", methods=["POST"])
@login_required
def admin_create_redis_record():
    data = request.get_json() or {}
    record = data.get("record")

    if not isinstance(record, dict):
        return jsonify({"success": False, "error": "A JSON object is required in 'record'"}), 400

    record_id = str(record.get("id", "")).strip() or str(get_next_object_id())
    if r.exists(record_id):
        return jsonify({"success": False, "error": f"Record {record_id} already exists"}), 400

    normalized = {
        k: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        for k, v in record.items()
    }
    normalized["id"] = record_id
    r.hset(record_id, mapping=normalized)
    refresh_runtime_indexes()

    return jsonify({"success": True, "id": record_id, "message": "Record created"}), 201


@app.route("/admin/api/redis/records/<record_id>", methods=["PUT"])
@login_required
def admin_update_redis_record(record_id):
    if not r.exists(record_id):
        return jsonify({"success": False, "error": "Record not found"}), 404

    data = request.get_json() or {}
    record = data.get("record")
    if not isinstance(record, dict):
        return jsonify({"success": False, "error": "A JSON object is required in 'record'"}), 400

    normalized = {
        k: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        for k, v in record.items()
    }
    normalized["id"] = record_id
    r.hset(record_id, mapping=normalized)
    refresh_runtime_indexes()

    return jsonify({"success": True, "id": record_id, "message": "Record updated"})


@app.route("/admin/api/redis/records/<record_id>", methods=["DELETE"])
@login_required
def admin_delete_redis_record(record_id):
    if not r.exists(record_id):
        return jsonify({"success": False, "error": "Record not found"}), 404

    r.delete(record_id)
    refresh_runtime_indexes()

    return jsonify({"success": True, "id": record_id, "message": "Record deleted"})
# ---------------------------------------------------------
# IMAGE ROUTES
# ---------------------------------------------------------
@app.route('/images/<filename>')
def get_image(filename):
    if not filename or filename == "default":
        filename = "default.jpeg"

    img_path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(img_path):
        return send_from_directory(IMAGES_DIR, filename)

    # Fallback to a repository-owned placeholder image when the requested asset
    # is missing from backend/downloaded_images. This prevents frontend 404s
    # from breaking cards, map popups, or collection covers.
    default_path = os.path.join(IMAGES_DIR, "default.jpeg")
    if os.path.exists(default_path):
        return send_from_directory(IMAGES_DIR, "default.jpeg")

    return send_from_directory(os.path.join(FRONTEND_STATIC_DIR, "img"), "logo.svg")

@app.route('/images/')
def get_default_image():
    default_path = os.path.join(IMAGES_DIR, "default.jpeg")
    if os.path.exists(default_path):
        return send_from_directory(IMAGES_DIR, "default.jpeg")

    return send_from_directory(os.path.join(FRONTEND_STATIC_DIR, "img"), "logo.svg")

@app.route('/static/js/modal.js')
def get_safe_modal_js():
    # Serve a defensive version of modal.js from Flask so pages that do not
    # include the favorite modal markup do not crash during script evaluation.
    script = """
const favoriteModal = document.getElementById('favoriteModal');
const closeBtn = document.getElementById('closeFavoriteModal');

async function openFavoriteModal(featureId, event) {
    if (!favoriteModal) return;

    currentObjectId = featureId;

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
        if (loginSection) loginSection.classList.add('hidden');
        if (collectionSection) collectionSection.classList.remove('hidden');
        if (typeof loadCollections === 'function') loadCollections();
    } else {
        if (loginSection) loginSection.classList.remove('hidden');
        if (collectionSection) collectionSection.classList.add('hidden');
    }

    favoriteModal.classList.remove('hidden');
}

function closeFavoriteModal() {
    if (!favoriteModal) return;
    favoriteModal.classList.add('hidden');
}

if (closeBtn) {
    closeBtn.addEventListener('click', closeFavoriteModal);
}

if (favoriteModal) {
    favoriteModal.addEventListener('click', (e) => {
        if (e.target === favoriteModal) closeFavoriteModal();
    });
}
"""
    return Response(script, mimetype='application/javascript')

@app.route('/static/js/map.js')
def get_runtime_map_js():
    # Serve the repository map.js plus a small runtime patch that makes the
    # map container visible in layouts where the legacy CSS would otherwise
    # collapse or hide it without producing a JavaScript error.
    map_js_path = os.path.join(FRONTEND_STATIC_DIR, "js", "map.js")
    with open(map_js_path, "r", encoding="utf-8") as map_js_file:
        script = map_js_file.read()

    script += """

window.addEventListener('load', () => {
    const mapWrapper = document.getElementById('map');
    const mapCanvas = document.getElementById('map-canvas');
    const mainContent = document.getElementById('main-content');

    if (mapWrapper) {
        mapWrapper.classList.add('active');
        mapWrapper.style.display = 'block';
        mapWrapper.style.position = 'relative';
        mapWrapper.style.width = '100%';
        mapWrapper.style.minHeight = 'calc(100vh - 180px)';
    }

    if (mainContent) {
        mainContent.style.position = 'relative';
        mainContent.style.width = '100%';
        mainContent.style.minHeight = 'calc(100vh - 180px)';
        mainContent.style.pointerEvents = 'auto';
    }

    if (mapCanvas) {
        mapCanvas.style.position = 'absolute';
        mapCanvas.style.inset = '0';
        mapCanvas.style.width = '100%';
        mapCanvas.style.height = '100%';
        mapCanvas.style.minHeight = 'calc(100vh - 180px)';
        mapCanvas.style.pointerEvents = 'auto';
    }

    setTimeout(() => {
        if (typeof map !== 'undefined' && map && typeof map.resize === 'function') {
            map.resize();
        }
    }, 300);
});
"""
    return Response(script, mimetype='application/javascript')

@app.route('/static/css/style.css')
def get_runtime_style_css():
    # Preserve the repository stylesheet and append a small override layer for
    # the map layout so the map remains visible in the integrated Flask setup.
    style_css_path = os.path.join(FRONTEND_STATIC_DIR, "css", "style.css")
    with open(style_css_path, "r", encoding="utf-8") as style_css_file:
        css = style_css_file.read()

    css += """

#map {
    position: relative !important;
    display: block;
    width: 100%;
    min-height: calc(100vh - 180px);
}

#map.active {
    display: block !important;
    min-height: calc(100vh - 180px);
}

#main-content {
    position: relative !important;
    width: 100%;
    min-height: calc(100vh - 180px);
    pointer-events: auto;
}

#map-canvas {
    position: absolute !important;
    inset: 0;
    width: 100%;
    height: 100%;
    min-height: calc(100vh - 180px);
    pointer-events: auto;
}
"""
    return Response(css, mimetype='text/css')

# ---------------------------------------------------------
# SEARCH (semantic)
# ---------------------------------------------------------
@app.route("/search", methods=["POST"])
def search():
    json_data = request.get_json()
    image_id = json_data.get("image_id", "").strip()  # <-- grab image_id
    k = json_data.get("k", 10)
    print("Received search request:", json_data)

    if not image_id:
        return jsonify([])

    # Find the object with this image_id in redis_objects
    obj = next((o for o in redis_objects if o.get("id") == image_id), None)
    if not obj:
        print(f"Image ID {image_id} not found")
        return jsonify([])

    # Fetch embedding (already stored as JSON string)
    emb_str = obj.get("embeddings")
    if not emb_str:
        print(f"No embedding for image ID {image_id}")
        return jsonify([])

    query_emb = np.array(json.loads(emb_str), dtype="float32").reshape(1, -1)

    # Make sure dimension matches FAISS index
    if query_emb.shape[1] != redis_faiss.d:
        print(f"Embedding dimension {query_emb.shape[1]} does not match FAISS index {redis_faiss.d}")
        return jsonify([])

    # Perform FAISS search
    D, I = redis_faiss.search(query_emb, min(k, len(redis_objects)))

    # Get the matching objects
    results = [redis_objects[idx] for idx in I[0]]

    return jsonify(results)

# ---------------------------------------------------------
# SEARCH KEYWORDS
# ---------------------------------------------------------
@app.route("/search_keywords", methods=["GET"])
def search_keywords():
    model = get_model()
    query = request.args.get("q", "").strip().lower()
    if not query or len(keyword_list) == 0 or model is None:
        return jsonify({"results": []})

    # Embed the query text
    query_emb = model.encode([query]).astype("float32")

    # Limit number of keyword matches
    k = min(10, len(keyword_list))
    D, I = keyword_faiss.search(query_emb, k)

    # Get matched keywords
    matched_keywords = [keyword_list[i] for i in I[0]]

    # Collect unique object IDs for matched keywords
    matched_ids = set()
    for kw in matched_keywords:
        matched_ids.update(keyword_map.get(kw, []))

    # Fetch the objects from Redis
    results = []
    for obj_id in matched_ids:
        obj = r.hgetall(f"{obj_id}")
        if obj:
            # Make sure each object includes an 'id' field for the frontend
            results.append({
                "id": obj.get("id", obj_id),
                "title": obj.get("title", ""),
                "description": obj.get("model_base", ""),
                "author": obj.get("author", ""),
                "origin": obj.get("origin", ""),
                "model_base": obj.get("model_base", ""),
                "singer": obj.get("singer", ""),
                "img_path": obj.get("img_path", "default.jpeg"),
                "fondo": obj.get("fondo", ""),
                "date": obj.get("date", ""),
                "image": obj.get("image", ""),
                "coordinates": obj.get("coordinates", "")
            })

    return jsonify({
        "matched_keywords": matched_keywords,
        "results": results[:10]  # limit to 10 results
    })

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
@app.route("/user/status", methods=["GET"])
def user_status():
    if "user" in session:
        return jsonify({"logged_in": True, "username": session["user"]})
    return jsonify({"logged_in": False})

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email = data.get("email", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Check if user exists
    if r_users.exists(f"user:{username}:data"):
        return jsonify({"error": "Username already exists"}), 400

    # Hash password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    # Store user
    r_users.hset(f"user:{username}:data", mapping={
        "password": hashed_password,
        "email": email,
        "created_at": str(datetime.datetime.utcnow())
    })

    return jsonify({"success": True, "message": "User registered successfully"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user_data = r_users.hgetall(f"user:{username}:data")
    if not user_data:
        return jsonify({"error": "Invalid username or password"}), 401

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    if hashed_password != user_data.get("password"):
        return jsonify({"error": "Invalid username or password"}), 401

    # Login success
    session.permanent = True  # <— this makes the session last as per PERMANENT_SESSION_LIFETIME
    session["user"] = username
    session.permanent = True  # optional, respects permanent_session_lifetime
    return jsonify({"success": True, "message": "Logged in successfully"})


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route("/user/collections", methods=["GET"])
@login_required
def list_collections():
    username = session["user"]
    collection_names = r_users.smembers(f"user:{username}:collections") or set()
    collections = []

    for name in collection_names:
        print(f"user:{username}:collection:{name}")
        # Get object IDs in this collection
        object_ids = r_users.smembers(f"user:{username}:collection:{name}") or set()
        print(object_ids)
        objects = []
        
        for obj_id in object_ids:
            #obj = r.hgetall(f"{obj_id}")
            # Find the object with this image_id in redis_objects
            obj = next((o for o in redis_objects if o.get("id") == obj_id), None)
            print(obj)
            if obj:
                objects.append({
                    "id": obj.get("id", obj_id),
                    "title": obj.get("title", ""),
                    "image": obj.get("image", ""),
                    "description": obj.get("model_base", "")
                })

        collections.append({
            "name": name,
            "objects": objects
        })

    return jsonify({"success": True, "collections": collections})


@app.route("/user/collections/create", methods=["POST"])
@login_required
def create_collection():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session["user"]
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Collection name required"}), 400

    # Add collection name to user's collections set
    r_users.sadd(f"user:{username}:collections", name)
    return jsonify({"success": True, "message": f"Collection '{name}' created."})

@app.route("/user/collections/add", methods=["POST"])
@login_required
def add_to_collection():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    username = session["user"]
    data = request.get_json()
    obj_id = str(data.get("object_id"))
    collection_name = data.get("collection_name", "").strip()
    if not obj_id or not collection_name:
        return jsonify({"error": "Missing object_id or collection_name"}), 400

    # Make sure collection exists
    if not r_users.sismember(f"user:{username}:collections", collection_name):
        return jsonify({"error": "Collection does not exist"}), 404

    # Add object to collection (as Redis set)
    r_users.sadd(f"user:{username}:collection:{collection_name}", obj_id)
    return jsonify({"success": True, "message": f"Object {obj_id} added to '{collection_name}'"})

@app.route("/api/collection/<collection_name>")
@login_required
def get_collection(collection_name):
    username = session["user"]

    key = f"user:{username}:collection:{collection_name}"

    if not r_users.exists(key):
        return jsonify({"success": False, "error": "Collection not found"}), 404

    object_ids = r_users.smembers(key)
    objects = []

    for obj_id in object_ids:
        obj = next((o for o in redis_objects if o.get("id") == obj_id), None)
        if obj:
            objects.append({
                "id": obj.get("id"),
                "title": obj.get("title", ""),
                "img_path": obj.get("img_path", ""),
                "image": obj.get("image", ""),
                "description": obj.get("model_base", "")
            })

    return jsonify({
        "success": True,
        "collection": collection_name,
        "objects": objects
    })

@app.route("/collection/<collection_name>")
@login_required
def collection_page(collection_name):
    username = session["user"]

    # check if collection exists for this user
    if not r_users.sismember(f"user:{username}:collections", collection_name):
        return "Collection not found or unauthorized", 404

    return render_template(
        "collection.html",
        collection_name=collection_name
    )

# ---------------------------------------------------------
# RUN APP
# ---------------------------------------------------------
if __name__ == "__main__":
    # The application is designed to be reachable both locally and from
    # external clients on the host network, so the default bind address is 0.0.0.0.
    # Port 8080 matches the externally reachable port currently used for access.
    app_host = os.environ.get("FLASK_HOST", "0.0.0.0")
    app_port = int(os.environ.get("FLASK_PORT", "8080"))
    cert_path = os.environ.get(
        "FLASK_CERT_PATH",
        os.path.join(PROJECT_ROOT, "infrastructure", "certs", "flask", "flask-cert.pem")
    )
    key_path = os.environ.get(
        "FLASK_KEY_PATH",
        os.path.join(PROJECT_ROOT, "infrastructure", "certs", "flask", "flask-key.pem")
    )
    use_ssl = os.environ.get("FLASK_USE_SSL", "true").lower() in {"1", "true", "yes", "on"}

    # SSL is enabled only when explicitly allowed and when both certificate
    # and key files are available. Otherwise Flask falls back to plain HTTP.
    ssl_context = None
    if use_ssl and os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_context = (cert_path, key_path)

    app.run(host=app_host, port=app_port, ssl_context=ssl_context)
