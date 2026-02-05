
import pytest
import os
from epopy import AsyncClient
from epopy.models import OPSResponse

# Mark as integration tests
pytestmark = pytest.mark.skipif(
    not os.getenv("EPO_CONSUMER_KEY") or not os.getenv("EPO_CONSUMER_SECRET"),
    reason="EPO credentials not found in environment"
)

@pytest.fixture
async def real_client() -> AsyncClient:
    key = os.getenv("EPO_CONSUMER_KEY")
    secret = os.getenv("EPO_CONSUMER_SECRET")
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
    
    # First get imagery info
    images_info = await real_client.published_data.published_data(
        "publication", pub_type, pub_num, "images"
    )
    
    # Find a link
    # The models might need to be checked for how they represent the images response
    # For now, let's use the raw get_data to find the link like in the workflow script
    # but the goal is to test the 'download_image' method.
    
    raw_images = await real_client.get_data(f"/published-data/publication/{pub_type}/{pub_num}/images")
    
    doc_instances = raw_images.get("ops:world-patent-data", {}).get("ops:document-inquiry", {}).get("ops:inquiry-result", {}).get("ops:document-instance", [])
    if isinstance(doc_instances, dict):
        doc_instances = [doc_instances]
        
    assert len(doc_instances) > 0
    
    link = doc_instances[0].get("@link")
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
