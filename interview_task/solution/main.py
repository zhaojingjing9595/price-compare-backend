from contextlib import asynccontextmanager

from fastapi import FastAPI
from db.database import engine, Base
from routers.stores import router as store_router
from routers.products import router as product_router

from services.refresh import refresh_all_prices
from services.scheduler import start_scheduler

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    refresh_task = start_scheduler()
    yield
    refresh_task.cancel()
    
app = FastAPI(title="Price Comparison API", lifespan=lifespan)


app.include_router(store_router)
app.include_router(product_router)


@app.post("/admin/refresh")
async def refresh_now():
    """Trigger a price refresh on demand, so the daily job can be demonstrated immediately."""
    return {"updated_listings": await refresh_all_prices()}

@app.get("/")
def root():
    return {'message': 'Hello World!'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9991)