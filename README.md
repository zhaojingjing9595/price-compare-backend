# Price Comparison API — Solution

A backend for an online-store price comparison platform. Stores (`ebay`, `amazon`)
are simulated by the containers in `internal/` and are reached only over HTTP. The
service registers stores and products, keeps prices fresh in a local MySQL database,
and answers product searches from that local copy.

## Design

The backend is three services, and every file maps onto one of them.

| # | Service | Trigger | Code |
|---|---------|---------|------|
| 1 | **Onboarding / cold start** | `POST /stores`, usually via `scripts/stores_onboard.py` | `services/sync.py: cold_start` |
| 2 | **Scheduler** | every 24h, in the app's lifespan | `services/sync.py: refresh_all_stores` |
| 3 | **Search** | `GET /products` | `services/search.py` |

Services 1 and 2 are the same operation on different triggers, so they share one
core — `sync_store()` — and differ only in *which* stores they run it for and how
failures are handled.

### Why prices are cached locally

- **Write path (background):** onboarding backfills a store's full catalog immediately;
  a daily job re-pulls every onboarded store and writes current prices into `product`.
- **Read path (`GET /products`):** a single local SQL query — a `LIKE '%…%'` scan
  joined to `store`. No outbound HTTP, so search stays fast however slow the stores
  are. The substring match is a table scan; see the note on `product.name` below.

Registering a store — not the scheduler — fires the first fetch, so a new store is
searchable within seconds instead of up to 24h later.

### Layout

```
solution/
├── main.py                 FastAPI app, scheduler wiring, GET /health
├── errors.py               domain errors → HTTP responses (registered from main.py)
├── routers/
│   ├── stores.py           POST /stores
│   └── products.py         POST /products, GET /products (search)
├── services/
│   ├── store_client.py     the ONLY outbound HTTP; store error types
│   ├── sync.py             shared sync core + cold start + daily refresh
│   └── search.py           the local search query
├── models/models.py        SQLAlchemy ORM: Store, Product
├── schemas/schemas.py      Pydantic request/response models
├── db/database.py          engine, session factory, get_db dependency
├── config/stores.yaml      stores to seed (…docker.yaml for in-compose URLs)
├── scripts/stores_onboard.py   seeds stores by calling POST /stores
└── tests/                  pytest, SQLite in-memory, get_db overridden
```

### Data model

| Table | Columns | Notes |
|---|---|---|
| `store` | `id`, `name` (unique, indexed), `api_endpoint`, `onboarded`, `last_synced_at`, `created_at` | `api_endpoint` is the single source of truth for where to fetch |
| `product` | `id`, `name`, `external_product_id`, `price`, `last_updated`, `store_id` FK | unique on `(name, store_id)`, which is also the only index covering `name` |

`onboarded` flips to `true` only after the first successful backfill, so a store that
was unreachable at registration is simply retried by the daily job.

### Error handling

`store_client.py` raises exactly two errors: `StoreUnavailableError` (network, timeout,
non-2xx) and `StoreDataError` (unparseable body, malformed listing).

- **Background paths** (cold start, refresh) catch and log them; a dead store never
  crashes a task, and one bad store never aborts the refresh cycle.
- **Request paths** let them bubble to the handlers in `errors.py` (registered from
  `main.py`), which return `503` — no repeated `try/except → HTTPException` in the routes.
- A malformed *listing* is skipped with a warning; the rest of the batch still lands.

The daily refresh runs stores concurrently (bounded by a semaphore), each in its own
`Session`, since a SQLAlchemy `Session` is not safe to share across concurrent tasks.

## API

Base URL: `http://localhost:8000`. Interactive docs at `/docs`.

### `POST /stores` — register a store and start its backfill

```json
{ "name": "ebay", "api_endpoint": "http://ebay-server:9991/products" }
```

Returns `202` immediately; the catalog backfill runs in the background.

```json
{ "store_id": 1, "name": "ebay", "status": "accepted",
  "message": "Store registered, catalog backfill started" }
```

- `409` — a store with that name is already registered

### `POST /products` — register a product and link it to a store

```json
{ "name": "Samsung Headphones S-104M", "external_product_id": "A-1", "store_id": 1 }
```

Seeds the price from the store's catalog so the product is searchable at once.

- `404` — store not found, or the store's catalog has no product with that exact name
- `409` — that product is already registered for that store
- `503` — the store is unreachable or returned an unusable response

### `GET /health` — liveness

```json
{ "status": "ok" }
```

### `GET /products?search_text=...` — search

```json
[
  {"product_name": "Samsung Headphones S-104M", "store_name": "amazon",
   "price": "10.59", "last_updated": "2026-09-01T10:00:00"},
  {"product_name": "Samsung Headphones S-104M", "store_name": "ebay",
   "price": "14.20", "last_updated": "2026-09-01T10:00:00"}
]
```

Sorted by price ascending; a product appears once per store offering it. No match
returns `[]`.

## Running

There are two ways to run the project. Pick one; you don't need both.

| | **A. Docker** (recommended) | **B. Without Docker** (local development) |
|---|---|---|
| Use it to | run the whole system and try it out | edit code with hot reload, run tests |
| You need | Docker + Docker Compose | Docker (for MySQL + the store simulators), Python 3.13, Node 22 |
| `.env` files | **not needed** | `solution/.env` required; `frontend/.env` optional |
| `npm install` / `pip install` | **not needed** (done inside the images) | needed |
| UI at | `http://localhost:3000` | `http://localhost:5173` |

All commands below are run from `interview_task/`, where `docker-compose.yml` lives.

---

### A. Running with Docker

No `.env` files, no `npm install`, no Python virtualenv: every dependency is installed
inside the images during the build.

**1. Start all five containers**

```bash
cd interview_task
docker compose up --build
```

| Container | Host port | Purpose |
|---|---|---|
| `ebay-server` | 8300 | simulated store |
| `amazon-server` | 8301 | simulated store |
| `mysql_db` | 33063 | MySQL; tables are created on API startup |
| `backend-server` | 8000 (→ 9991 in the container) | the FastAPI app |
| `frontend` | 3000 (→ 80 in the container) | the React UI, served by nginx |

These host ports must be free. The backend gets `DATABASE_URL` directly from
`docker-compose.yml`.

The frontend's `Dockerfile` is a two-stage build. A `node:22-alpine` stage runs
`npm ci && npm run build`, then only the resulting static `dist/` is copied into an
`nginx:alpine` stage. nginx serves the UI and also acts as the reverse proxy for `/api`
(see `frontend/nginx.conf`).

**2. Seed the stores** (in a second terminal, once the containers are up)

Until stores are registered, every search returns `[]`. This registers `ebay` and
`amazon` and triggers their first catalog pull:

```bash
docker compose exec backend-server python scripts/stores_onboard.py \
  --api-url http://localhost:9991
```

Running the script inside the API container means nothing extra has to be installed
on your machine. It's re-runnable (existing stores are skipped), and afterwards the
scheduler refreshes prices every 24h. To run it from your own machine instead, see
[Seeding the stores](#seeding-the-stores-reference).

**3. Verify**

```bash
docker compose logs -f backend-server                        # expect "[cold start] ebay: N products backfilled"
curl 'http://localhost:8000/products?search_text=Samsung'    # cheapest first, one row per store
curl 'http://localhost:8000/products?search_text=zzz'        # []
```

Or open `http://localhost:3000` and search "Samsung". Interactive API docs are at
`http://localhost:8000/docs`.

**Rebuilding and resetting**

Code is baked into the images, so rebuild after editing:

```bash
docker compose up -d --build backend-server   # after backend changes
docker compose up -d --build frontend         # after UI changes
docker compose down -v                        # stop everything and wipe the MySQL volume
```

---

### B. Running without Docker (local development)

The backend and frontend run on your machine with hot reload. MySQL and the two store
simulators still run in Docker, since they're dependencies rather than code you're
editing.

**1. Start the dependencies only**

```bash
cd interview_task
docker compose up ebay-server amazon-server mysql_db
```

**2. Backend** (new terminal, from `interview_task/`)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # requirements.txt is in interview_task/, not solution/
cd solution
cp .env.example .env                       # required: provides DATABASE_URL
uvicorn main:app --reload --port 8000
```

`solution/.env` is required here: `db/database.py` reads `DATABASE_URL` at import time
and fails without it. The example value points at the Docker MySQL on host port 33063.

**3. Seed the stores** (from `interview_task/solution/`, venv active)

```bash
python scripts/stores_onboard.py --config config/stores.yaml
```

`config/stores.yaml` uses `localhost` store URLs (ports 8300/8301), which are what a
backend running on your machine can reach.

**4. Frontend** (new terminal, from `interview_task/`)

```bash
cd frontend
npm install
cp .env.example .env    # optional: only if the backend is somewhere other than localhost:8000
npm run dev
```

Opens at `http://localhost:5173`. Vite proxies `/api/*` to `API_PROXY_TARGET` from
`frontend/.env`, and falls back to `http://localhost:8000` when it isn't set, so with
the backend from step 2 the `.env` file can be skipped.

> **Mixing the two:** you can also run only the frontend with `npm run dev` against the
> full Docker stack from option A. The backend is still on `localhost:8000`, so no
> extra configuration is needed.

**5. Tests** (from `interview_task/solution/`, venv active)

```bash
pytest
```

Tests use in-memory SQLite and override `get_db`, so they need neither MySQL nor a
`.env` file.

---

### Seeding the stores (reference)

`scripts/stores_onboard.py` takes two settings, and each depends on where something runs:

- **`--api-url`** depends on where the *script* runs. It's the address the script uses
  to reach the API. Default: `$API_URL`, or `http://localhost:8000`.
- **`--config`** depends on where the *backend* runs. The `api_endpoint` values in it
  are stored and later fetched by the backend, so they must be reachable from there.
  A backend in Docker needs `config/stores.docker.yaml` (compose service names, the
  default). A backend on your machine needs `config/stores.yaml` (`localhost` ports).

| Script runs on | Backend runs in | `--api-url` | `--config` |
|---|---|---|---|
| API container | Docker (option A) | `http://localhost:9991` (uvicorn's port inside the container) | `config/stores.docker.yaml` (default) |
| Your machine | Docker (option A) | `http://localhost:8000` (default) | `config/stores.docker.yaml` (default) |
| Your machine | Your machine (option B) | `http://localhost:8000` (default) | `config/stores.yaml` |

Running the script from your machine requires the Python setup from option B, step 2
(`httpx`, `pyyaml` and `python-dotenv` must be installed).

Store URLs are **not** environment variables. They live in `config/stores*.yaml` and
are persisted per store at onboarding.

---

### How frontend API calls actually reach the backend

The frontend code never calls the backend's real address. Every request goes through
`src/api/api.ts`, which always calls a relative `/api/...` path:

```ts
const API_BASE = '/api'
fetch(`${API_BASE}/products`)   // → /api/products
fetch(`${API_BASE}/stores`)     // → /api/stores
```

Whatever is in front of the frontend rewrites `/api/...` to `/...` and forwards it to
wherever the backend actually is. Which proxy that is, and the backend address it
forwards to, depends on how the frontend is running:

| Frontend running via | What proxies `/api` | Browser requests | Gets rewritten/forwarded to |
|---|---|---|---|
| Option A: `docker compose up` (nginx, port 3000) | `nginx.conf`'s `location /api/ { proxy_pass http://backend-server:9991/; }` | `http://localhost:3000/api/products` | `http://backend-server:9991/products`, reachable because nginx is on the same `store_exercise_1` Docker network as the backend |
| Option B: `npm run dev` (Vite, port 5173), backend in Docker | Vite's `server.proxy` in `vite.config.ts`, target `API_PROXY_TARGET` (default `http://localhost:8000`) | `http://localhost:5173/api/products` | `http://localhost:8000/products`, the host-published port, which Docker forwards to the container's 9991 |
| Option B: `npm run dev` (Vite, port 5173), backend via `uvicorn --port 8000` on your machine | Same Vite proxy, same target | `http://localhost:5173/api/products` | `http://localhost:8000/products` directly on your machine |

In every case the `/api` prefix is stripped during the rewrite. nginx does it with the
trailing slashes (`/api/` → `/`) and Vite with an explicit
`rewrite: (path) => path.replace(/^\/api/, '')`. The backend's own routes
(`routers/products.py`, `routers/stores.py`) are mounted at `/products` and `/stores`,
not `/api/products`.

This indirection lets the same frontend bundle run unmodified in Docker or in dev. Only
the proxy's *target* changes between environments (`nginx.conf` baked into the image vs.
Vite's `API_PROXY_TARGET`), never the frontend's own code. It also avoids CORS entirely,
since the browser only ever talks to one origin: whichever proxy is in front of it.
