import pytest

from httpx import Response

from typing import Any
from epopy import AsyncClient

@pytest.mark.asyncio
async def test_client_request_headers(client: AsyncClient, mock_token: None, respx_mock: Any) -> None:
    route = respx_mock.get("https://ops.epo.org/3.2/rest-services/endpoint").mock(
        return_value=Response(200, text="<root><data>ok</data></root>")
    )
    
    await client.request("GET", "/endpoint")
    
    assert route.called
    headers = route.calls.last.request.headers
    assert headers["Authorization"] == "Bearer mock_token"
    assert headers["Accept"] == "application/xml"

@pytest.mark.asyncio
async def test_get_data_parsing(client: AsyncClient, mock_token: None, respx_mock: Any) -> None:
    xml_response = """
    <ops:world-patent-data xmlns:ops="http://ops.epo.org">
        <ops:biblio-search>
            <ops:query>ti=plastic</ops:query>
        </ops:biblio-search>
    </ops:world-patent-data>
    """
    respx_mock.get("https://ops.epo.org/3.2/rest-services/search").mock(
        return_value=Response(200, text=xml_response)
    )
    
    data = await client.get_data("/search")
    
    assert "ops:world-patent-data" in data
    assert data["ops:world-patent-data"]["ops:biblio-search"]["ops:query"] == "ti=plastic"
