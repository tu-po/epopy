from typing import Literal
from ..client import AsyncClient
from ..models import OPSResponse

class RetrievalService:
    def __init__(self, client: AsyncClient):
        self.client = client
        
    async def published_data(
        self,
        reference_type: Literal["publication", "application", "priority"],
        input_format: Literal["docdb", "epodoc"],
        number: str,
        endpoint: Literal["biblio", "abstract", "full-cycle", "claims", "description", "fulltext", "images"] = "biblio"
    ) -> OPSResponse:
        """
        Retrieve published data.
        
        Args:
            reference_type: Type of reference (publication, application, priority)
            input_format: Format of the input number (docdb, epodoc)
            number: The patent number
            endpoint: The specific data to retrieve (biblio, abstract, etc.)
        """
        url = f"/published-data/{reference_type}/{input_format}/{number}/{endpoint}"
        data = await self.client.get_data(url)
        return OPSResponse(**data)

    async def download_image(
        self, 
        path: str, 
        range_position: int | str = 1, 
        document_format: str = "application/pdf"
    ) -> bytes:
        """
        Download a specific image variant (document instance).
        
        Args:
            path: The link/path to the image resource (e.g. from document-instance @link)
            range_position: The page range/position (required by OPS for images). Can be "1-10", "1", etc.
            document_format: The expected format (Accept header)
            
        Returns:
            The raw bytes of the image/document.
        """
        response = await self.client.get(
            path, 
            headers={"Accept": document_format}, 
            params={"range": str(range_position)}
        )
        return response.content
