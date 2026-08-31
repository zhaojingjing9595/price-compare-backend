# Price Comparison API — Solution

A backend for an online-store price comparison platform. Stores
(`amazon`, `ebay`) are simulated by the containers in `internal/` and are reached only over HTTP. The service registers stores and products, keeps prices fresh in a local MySQL database, and answers product searches from that local copy.

## Design

### Why prices are cached locally

- **Write path (background):** a daily refresh job pulls each store's full products list and writes current prices into the `product` table.
- **Read path (`GET /products`):** a single indexed SQL query against the local table. No outbound HTTP, so search stays in the low milliseconds regardless of how slow the stores are. 
-  A cached backed solution might be considered for improvement.

### Layers

```
solution/
├── main.py                 FastAPI app
├── routers/
│   ├── stores.py           POST /stores
│   └── products.py         POST /products, GET /products (search)
├── services/
│   ├── store_client.py     for the store simulators
│   ├── products.py         registration products + search query
│   ├── refresh.py          price refresh
│   └── scheduler.py        asyncio loop: refresh on startup, then every 24h
├── models/models.py        SQLAlchemy ORM: Store, Product
├── schemas/schemas.py      Pydantic request/response models
├── db/database.py          engine, session factory, get_db dependency
└── tests/                  pytest, SQLite in-memory, get_db overridden
```

### Data model

| Table | Columns | Notes |
|---|---|---|
| `store` | `id`, `name` (unique, indexed), `created_at` | 
| `product` | `id`, `name` (indexed), `external_product_id`, `price`, `last_updated`, `store_id` FK | unique on `(name, store_id)` |


## API

Base URL: `http://localhost:8000`. Interactive docs at `/docs`.

### `POST /stores` — register a store

```json
{ "id": 1, "name": "amazon", "created_at": "2026-09-01T10:00:00" }
```


### `POST /products` — register a product and link it to a store

- `404` — store not found, or the store's catalog has no such product
- `409` — that product is already registered for that store


### `GET /products?search_text=...` — search

```json
[
  {"product_name": "Samsung Headphones S-104M", "store_name": "amazon",
   "price": "10.59", "last_updated": "2026-09-01T10:00:00"},
  {"product_name": "Samsung Headphones S-104M", "store_name": "ebay",
   "price": "14.20", "last_updated": "2026-09-01T10:00:00"}
]
```

## Running

```bash
docker compose up --build
```

Brings up `amazon-server` (8300), `ebay-server` (8301), `mysql_db` (33063) and
the API (8000). Tables are created on startup; the refresh loop runs once
immediately, then every 24 hours.

### Environment

Copy `solution/.env.example` to `solution/.env`. 

### Running outside Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up ebay-server amazon-server mysql_db   # deps only
cd solution && uvicorn main:app --reload --port 8000
```