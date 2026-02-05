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
