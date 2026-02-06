from typing import Any, List
from httpx import Response
import pytest
from epopy import AsyncClient
from epopy.patent import Patent, Document

@pytest.mark.asyncio
async def test_patent_abstraction_mock(client: AsyncClient, mock_token: None, respx_mock: Any) -> None:
    # Mock imagery inquiry
    respx_mock.get("https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/EP1234567/images").mock(
        return_value=Response(200, content='''<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns:ops="http://ops.epo.org">
    <ops:document-inquiry>
        <ops:inquiry-result>
            <ops:document-instance desc="Drawing" link="path/to/img" number-of-pages="1">
                <ops:document-format-options>
                    <ops:document-format>application/pdf</ops:document-format>
                </ops:document-format-options>
            </ops:document-instance>
        </ops:inquiry-result>
    </ops:document-inquiry>
</ops:world-patent-data>''')
    )

    patent: Patent = client.get_patent("EP1234567")
    docs: List[Document] = await patent.get_documents()
    
    assert len(docs) == 1
    doc = docs[0]
    assert doc.name == "Drawing"
    assert doc.link == "path/to/img"
    
    # Mock download
    respx_mock.get("https://ops.epo.org/3.2/rest-services/path/to/img?range=1").mock(
        return_value=Response(200, content=b"fake_pdf")
    )
    
    content = await doc.download()
    assert content == b"fake_pdf"


