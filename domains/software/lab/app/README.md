# inventory-service

Inventory lookup + restock microservice (stdlib-only HTTP server).

## Endpoints

- `GET /health` -> `{"status": "ok"}`
- `GET /items/<sku>` -> item record or 404
- `POST /restock` -> apply `{sku: qty_delta}` deltas, returns new quantities

## Environment variables

- `CACHE_TTL` - seconds an item cache entry stays fresh (default: 30)
- `MAX_CONNECTIONS` - server connection cap (default: 8)

## Run locally

    python app.py            # listens on 0.0.0.0:8080

## Tests

    python -m unittest discover -s tests -p "test_*.py"

## Lint

    ruff check .
