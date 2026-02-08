import asyncio
import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from epopy.client import AsyncClient

CONSUMER_KEY = "GwHfSU69o9zS2JA4VgPvAnoe1QN7tCrcxQA6ArQUoFYCEzXr"
CONSUMER_SECRET = "qmcqxn56UaMqTljudJcrlOZs214SNK9hslCsTWmqoQp1nrPXcnI6ZoFRsRRxTA5r"

async def main():
    async with AsyncClient(CONSUMER_KEY, CONSUMER_SECRET) as client:
        print("Authenticating...")
        token = await client.auth.get_access_token()
        print(f"Got token: {token[:10]}...")
        
        print("\nFetching sample search (ti=plastic)...")
        # Search for title=plastic
        response = await client.get("/published-data/search?q=ti=plastic")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        print("\nFetching sample biblio (EP1000000)...")
        # Get biblio for EP1000000
        # Format: /published-data/{type}/{format}/{number}/biblio
        response = await client.get("/published-data/publication/epodoc/EP1000000/biblio")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
