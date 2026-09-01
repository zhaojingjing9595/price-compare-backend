"""Onboard every store listed in a YAML config by calling POST /stores.

Re-runnable: stores that already exist are reported and skipped. This is what a
deploy step or an admin runs once to seed the system, or again whenever a new
store is added to the YAML file.

Usage:
    python scripts/stores_onboard.py
    python scripts/stores_onboard.py --api-url http://localhost:8000 --config config/stores.yaml
"""

import argparse
import os
import sys

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv()

REQUEST_TIMEOUT_SECONDS = 10


def load_stores(config_path: str):
    with open(config_path) as f:
        return (yaml.safe_load(f) or {}).get("stores", [])


def onboard_store(api_url: str, store: dict):
    """Register one store. Returns True if it was newly onboarded."""
    name = store["name"]
    try:
        resp = httpx.post(
            f"{api_url}/stores",
            json={"name": name, "api_endpoint": store["api_endpoint"]},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        print(f"  x {name}: could not reach the API ({exc})")
        return False
    except KeyError as exc:
        print(f"  x {name}: missing config key {exc}")
        return False

    if resp.status_code == 202:
        print(f"  + {name}: onboarded (store_id={resp.json()['store_id']}, backfill started)")
        return True
    if resp.status_code == 409:
        print(f"  - {name}: already exists, skipping")
        return False
    print(f"  x {name}: failed ({resp.status_code}) {resp.text}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Onboard stores from a YAML config.")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("API_URL", "http://localhost:8000"),
        help="Base URL of the running API",
    )
    parser.add_argument("--config", default="config/stores.yaml", help="Path to the stores YAML")
    args = parser.parse_args()

    try:
        stores = load_stores(args.config)
    except (FileNotFoundError, yaml.YAMLError) as exc:
        sys.exit(f"Could not read {args.config}: {exc}")

    if not stores:
        print("No stores found in config.")
        return

    print(f"Onboarding {len(stores)} store(s) against {args.api_url} ...\n")
    onboarded = sum(onboard_store(args.api_url.rstrip('/'), s) for s in stores)

    print(f"\nDone: {onboarded} newly onboarded. Backfills run in the background —")
    print("check the API logs or GET /products to confirm the data landed.")


if __name__ == "__main__":
    main()
