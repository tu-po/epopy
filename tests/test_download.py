
import pytest
from httpx import Response
from typing import Any
from epopy import AsyncClient

@pytest.mark.asyncio
async def test_download_image_success(client: AsyncClient, mock_token: None, respx_mock: Any) -> None:
    # Use a relative path as seen in OPS responses usually, or absolute
    # If the user passes a relative path, the client should handle it relative to base URL?
    # Actually, in test_workflow we saw "published-data/images/..."
    # client.request handles lstrip and base_url.
    
    image_path = "published-data/images/EP/2950346/A2/thumbnail"
    expected_url = "https://ops.epo.org/3.2/rest-services/published-data/images/EP/2950346/A2/thumbnail"
    
    route = respx_mock.get(expected_url).mock(
        return_value=Response(
            200, 
            content=b"%PDF-1.4...", 
            headers={"Content-Type": "application/pdf"}
        )
    )
    
    content = await client.published_data.download_image(image_path)
    
    assert content == b"%PDF-1.4..."
    
    # Verify headers and params
    last_request = route.calls.last.request
    assert last_request.headers["Accept"] == "application/pdf"
    assert last_request.url.params["range"] == "1"

@pytest.mark.asyncio
async def test_download_image_custom_params(client: AsyncClient, mock_token: None, respx_mock: Any) -> None:
    image_path = "published-data/images/EP/2950346/A2/fullimage"
    expected_url = "https://ops.epo.org/3.2/rest-services/published-data/images/EP/2950346/A2/fullimage"
    
    route = respx_mock.get(expected_url).mock(
        return_value=Response(200, content=b"TIFF_DATA")
    )
    
    await client.published_data.download_image(
        image_path, 
        range_position=2, 
        document_format="application/tiff"
    )
    
    last_request = route.calls.last.request
    assert last_request.headers["Accept"] == "application/tiff"
    assert last_request.url.params["range"] == "2"
