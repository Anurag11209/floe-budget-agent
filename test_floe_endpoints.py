#!/usr/bin/env python3
"""
Test script to probe Floe API endpoints and discover correct paths.
Run this to diagnose endpoint issues before running the agent.
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

FLOE_API_KEY = os.getenv("FLOE_API_KEY")
BASE_URL = "https://credit-api.floelabs.xyz"

async def test_endpoint(client: httpx.AsyncClient, method: str, path: str, data: dict = None):
    """Test a single endpoint and report results."""
    try:
        if method.upper() == "GET":
            resp = await client.get(path)
        else:
            resp = await client.post(path, json=data or {})

        print(f"✓ {method.upper()} {path}")
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        return True
    except Exception as e:
        print(f"✗ {method.upper()} {path}")
        print(f"  Error: {str(e)}")
        return False

async def main():
    print(f"Testing Floe API at {BASE_URL}")
    print(f"Using API Key: {FLOE_API_KEY[:20]}...")
    print("=" * 60)

    if not FLOE_API_KEY:
        print("ERROR: FLOE_API_KEY not set in .env")
        return

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={
            "Authorization": f"Bearer {FLOE_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
        verify=False,
    ) as client:

        # Test paths from current FloeClient
        endpoints_to_test = [
            # Current paths that return 404
            ("GET", "/v1/credit/status", None),
            ("POST", "/v1/x402/estimate", {"endpoints": []}),
            ("GET", "/v1/intents/lend", None),
            ("POST", "/v1/intents/borrow", {"amount_usdc": 100}),
            ("POST", "/v1/loans/repay", {"loan_id": "test"}),

            # Alternative paths to try
            ("GET", "/credit/status", None),
            ("GET", "/v1/loans/status", None),
            ("GET", "/v1/credit", None),
            ("POST", "/v1/borrow", {"amount_usdc": 100}),
            ("POST", "/borrow", {"amount_usdc": 100}),
            ("GET", "/status", None),

            # x402 alternatives
            ("POST", "/x402/estimate", {"endpoints": []}),
            ("POST", "/v1/x402", {"url": "test"}),
        ]

        print("\nTesting Endpoints:")
        print("-" * 60)

        for method, path, data in endpoints_to_test:
            await test_endpoint(client, method, path, data)
            print()

if __name__ == "__main__":
    asyncio.run(main())
