import pytest

from httpx import Response
from epopy.models import OPSResponse

from typing import Any
from epopy import AsyncClient

@pytest.mark.asyncio
async def test_search_service(client: AsyncClient, mock_token: None, respx_mock: Any) -> None:
    xml_response = """
    <ops:world-patent-data xmlns:ops="http://ops.epo.org">
        <ops:biblio-search total-result-count="10">
            <ops:query>ti=plastic</ops:query>
            <ops:search-result>
                <ops:publication-reference>
                    <document-id document-id-type="docdb">
                        <country>EP</country>
                        <doc-number>1000000</doc-number>
                        <kind>A1</kind>
                    </document-id>
                </ops:publication-reference>
            </ops:search-result>
        </ops:biblio-search>
    </ops:world-patent-data>
    """
    respx_mock.get("https://ops.epo.org/3.2/rest-services/published-data/search").mock(
        return_value=Response(200, text=xml_response)
    )
    
    response = await client.search.published_data_search("ti=plastic")
    
    assert isinstance(response, OPSResponse)
    assert response.world_patent_data.biblio_search is not None
    assert response.world_patent_data.biblio_search.total_result_count == 10
    assert response.world_patent_data.biblio_search.query == "ti=plastic"

@pytest.mark.asyncio
async def test_retrieval_service(client: AsyncClient, mock_token: None, respx_mock: Any) -> None:
    xml_response = """
    <ops:world-patent-data xmlns:ops="http://ops.epo.org">
        <exchange-documents>
            <exchange-document country="EP" doc-number="1000000" kind="A1">
                <bibliographic-data>
                    <publication-reference>
                        <document-id>
                            <country>EP</country>
                            <doc-number>1000000</doc-number>
                        </document-id>
                    </publication-reference>
                </bibliographic-data>
            </exchange-document>
        </exchange-documents>
    </ops:world-patent-data>
    """
    url = "https://ops.epo.org/3.2/rest-services/published-data/publication/epodoc/EP1000000/biblio"
    respx_mock.get(url).mock(
        return_value=Response(200, text=xml_response)
    )
    
    response = await client.published_data.published_data(
        "publication", "epodoc", "EP1000000", "biblio"
    )
    
    assert isinstance(response, OPSResponse)
    assert response.world_patent_data.exchange_documents is not None
    assert response.world_patent_data.exchange_documents.exchange_document is not None
    # Adjust for list/item union
    exch_doc = response.world_patent_data.exchange_documents.exchange_document
    if isinstance(exch_doc, list):
         assert exch_doc[0].country == "EP"
    else:
         assert exch_doc.country == "EP"
