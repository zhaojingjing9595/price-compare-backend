import os
from dotenv import load_dotenv

load_dotenv()

def get_store_base_url(store_name: str):
    url = os.environ.get(f"{store_name.upper()}_URL")
    return url.rstrip("/") if url else None
