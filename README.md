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

```bash
docker compose up --build
```

Brings up `ebay-server` (8300), `amazon-server` (8301), `mysql_db` (33063) and the
API (8000). Tables are created on startup.

Then seed the stores — this triggers the first catalog pull. Run it *inside* the API
container, so the stored `api_endpoint` is a compose service name and not `localhost`:

```bash
docker compose exec backend-server python scripts/stores_onboard.py \
  --api-url http://localhost:9991 --config config/stores.docker.yaml
```

Re-runnable: existing stores are skipped. After that the scheduler refreshes every 24h.

### Manual verification

```bash
docker compose logs -f backend-server                        # expect "[cold start] ebay: N products backfilled"
curl 'http://localhost:8000/products?search_text=Samsung'    # cheapest first, one row per store
curl 'http://localhost:8000/products?search_text=zzz'        # []
```

Code is baked into the image, so rebuild after editing: `docker compose up -d --build
backend-server`. MySQL persists in a volume — `docker compose down -v` for a clean run.

### Environment

Copy `solution/.env.example` to `solution/.env`. Store URLs are **not** environment
variables — they live in `config/stores.yaml` and are persisted per store at onboarding.

### Running outside Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # at interview_task/, not solution/
docker compose up ebay-server amazon-server mysql_db   # deps only
cd solution && uvicorn main:app --reload --port 8000
python scripts/stores_onboard.py --config config/stores.yaml
```

### Tests

```bash
cd solution && pytest
```
