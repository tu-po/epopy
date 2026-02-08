
import pytest
import os
from typing import AsyncGenerator, cast, List, Dict, Any
from io import BytesIO
from pypdf import PdfReader
from epopy import AsyncClient
from epopy.models import OPSResponse

# Mark as integration tests
pytestmark = pytest.mark.skipif(
    not os.getenv("EPO_CONSUMER_KEY") or not os.getenv("EPO_CONSUMER_SECRET"),
    reason="EPO credentials not found in environment"
)

@pytest.fixture
async def real_client() -> AsyncGenerator[AsyncClient, None]:
    key = os.getenv("EPO_CONSUMER_KEY", "")
    secret = os.getenv("EPO_CONSUMER_SECRET", "")
    if not key or not secret:
        pytest.skip("EPO credentials not found in environment")
    async with AsyncClient(key, secret) as client:
        yield client

@pytest.mark.asyncio
async def test_real_search(real_client: AsyncClient) -> None:
    # Test with a known patent
    response = await real_client.search.published_data_search("ti=plastic")
    assert isinstance(response, OPSResponse)
    assert response.world_patent_data.biblio_search is not None
    assert response.world_patent_data.biblio_search.total_result_count > 0

@pytest.mark.asyncio
async def test_real_download(real_client: AsyncClient) -> None:
    # Test download with a known document (T 3069/19 -> EP 2950346)
    # Note: We need a valid path from the images endpoint
    pub_type = "docdb"
    pub_num = "EP.2950346.A2"
    
    # First get imagery info to check if docs exist
    await real_client.published_data.published_data(
        "publication", pub_type, pub_num, "images"
    )
    
    # Find a link
    # The models might need to be checked for how they represent the images response
    # For now, let's use the raw get_data to find the link like in the workflow script
    # but the goal is to test the 'download_image' method.
    
    raw_images = await real_client.get_data(f"/published-data/publication/{pub_type}/{pub_num}/images")
    
    doc_instances_raw = raw_images.get("ops:world-patent-data", {}).get("ops:document-inquiry", {}).get("ops:inquiry-result", {}).get("ops:document-instance", [])
    doc_instances = cast(List[Dict[str, Any]], [doc_instances_raw] if isinstance(doc_instances_raw, dict) else doc_instances_raw)
    
    assert len(doc_instances) > 0
    
    # We take the first one
    doc = doc_instances[0]
    link = cast(str, doc.get("@link"))
    assert link is not None
    
    # Download the thumbnail or drawing
    content = await real_client.published_data.download_image(link, range_position=1)
    assert len(content) > 0
    # Basic PDF check if it's application/pdf
    if content.startswith(b"%PDF"):
        assert True
    else:
        # Might be TIFF or something else depending on OPS, but at least we got bytes
        assert len(content) > 100
@pytest.mark.asyncio
async def test_real_patent_abstractions(real_client: AsyncClient) -> None:
    # Test the high-level Patent/Document integration
    patent = real_client.get_patent("EP.2950346.A2")
    assert patent.number == "EP.2950346.A2"
    
    docs = await patent.get_documents()
    assert len(docs) > 0
    
    # Check document attributes
    doc = docs[0]
    assert doc.name is not None
    assert doc.type is not None
    assert len(doc.formats) > 0
    
    # Test download via Document abstraction
    content = await doc.download()
    assert len(content) > 0
    assert content.startswith(b"%PDF") or len(content) > 100
    assert content.startswith(b"%PDF") or len(content) > 100

@pytest.mark.asyncio
async def test_real_pdf_page_count(real_client: AsyncClient) -> None:
    # Regression test for "1 page download" bug
    # Target EP3829124 which is known to have ~59 pages
    patent = real_client.get_patent("EP.3829124.A1")
    docs = await patent.get_documents()
    
    full_doc = next((d for d in docs if d.name == "FullDocument"), None)
    assert full_doc is not None, "FullDocument not found for EP3829124"
    assert full_doc.number_of_pages is not None
    assert full_doc.number_of_pages > 10, f"Expected >10 pages, metadata says {full_doc.number_of_pages}"
    
    print(f"Downloading {full_doc.number_of_pages} pages...")
    content = await full_doc.download()
    
    reader = PdfReader(BytesIO(content))
    actual_pages = len(reader.pages)
    
    print(f"Downloaded {len(content)} bytes, {actual_pages} pages")
    
    # Assert we got the full document, not just 1 page
    assert actual_pages > 1, "Downloaded PDF has only 1 page!"
    assert actual_pages == full_doc.number_of_pages, f"Page count mismatch: expected {full_doc.number_of_pages}, got {actual_pages}"
