# epopy

Async Python client for the EPO Open Patent Services (OPS) API.

## Installation

```bash
pip install epopy
```

For development:

```bash
pip install epopy[dev]
```

## Usage

```python
import asyncio
from epopy import AsyncClient

async def main():
    async with AsyncClient(consumer_key="YOUR_KEY", consumer_secret="YOUR_SECRET") as client:
        # Search patents
        results = await client.search_patents("ti=solar AND pa=siemens")
        
        # Get a specific patent
        patent = client.get_patent("EP1234567")
        biblio = await patent.biblio()
        
        # Download documents
        pdf_bytes = await patent.download_document("FullDocument")

asyncio.run(main())
```

## Features

- Async/await API using `httpx`
- Patent search via CQL queries
- Bibliographic data retrieval
- Document and image downloads
- EPO Boards of Appeal decisions parsing

## Requirements

- Python 3.12+
- EPO OPS API credentials ([register here](https://developers.epo.org/))

## License

AGPL-3.0-only
