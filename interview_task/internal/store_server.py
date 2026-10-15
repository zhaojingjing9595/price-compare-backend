"""
Peeking at the store_server code?
Well, this is a simple FastAPI server that serves a list of products from a JSON file.
This code is very messy on purpose. We expect from you better code organization and quality.
So do not take this as a reference.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import aiofiles
import json
import asyncio
import os
import datetime
from random import randint


STORE_NAME = os.getenv("STORE_NAME", "unknown")
PRODUCTS_FILE_PATH = f'{STORE_NAME}_products.json'
PRICE_UPDATE_INTERVAL_MINUTES = int(os.getenv("PRICE_UPDATE_INTERVAL_MINUTES", "5"))

app = FastAPI()
logger = logging.getLogger("uvicorn")


async def load_json_file(filepath):
    async with aiofiles.open(filepath, 'r') as file:
        content = await file.read()
        data = json.loads(content)
        return data


async def load_products():
    all_products = await load_json_file(PRODUCTS_FILE_PATH)
    all_products = await update_prices_if_needed(all_products)
    return all_products


async def update_prices_if_needed(products: list):
    last_price_update_ts = os.getenv("LAST_PRICE_UPDATE_TS")
    now = datetime.datetime.now(datetime.timezone.utc)
    if last_price_update_ts:
        last_ts = datetime.datetime.fromisoformat(last_price_update_ts)
        if now - last_ts < datetime.timedelta(minutes=PRICE_UPDATE_INTERVAL_MINUTES):
            return products
    for p in products:
        p['price'] = p['price'] + randint(1, 100)
    async with aiofiles.open(PRODUCTS_FILE_PATH, 'w') as file:
        await file.write(json.dumps(products, indent=4))
    os.environ["LAST_PRICE_UPDATE_TS"] = now.isoformat()
    return products


@app.get("/products")
async def get_all(request: Request):
    params = dict(request.query_params)

    await asyncio.sleep(2)
    all_products = await load_products()
    filtered_products = all_products
    if 'name_contains' in params:
        filtered_products = [p for p in all_products if params['name_contains'] in p['name']]
    logger.info(f'Store {STORE_NAME}: Received GET request with params {params}')

    response = {
        "store": STORE_NAME,
        "products": filtered_products
    }

    return JSONResponse(status_code=200, content=response)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9991)
