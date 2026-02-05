from typing import Optional
from ..client import AsyncClient
from ..models import OPSResponse

class SearchError(Exception):
    pass

class SearchService:
    def __init__(self, client: AsyncClient):
        self.client = client
        
    async def published_data_search(
        self, 
        cql: str, 
        start: int = 1, 
        end: int = 25, 
        constituents: Optional[str] = None
    ) -> OPSResponse:
        """
        Search for published data.
        
        Args:
            cql: Contextual Query Language string (e.g. 'ti=plastic')
            start: Start index (1-based)
            end: End index
            constituents: Optional constituent (e.g. 'abstract')
        """
        range_header = f"{start}-{end}"
        params = {"q": cql}
        
        url = "/published-data/search"
        if constituents:
            url = f"{url}/{constituents}"
            
        data = await self.client.get_data(
            url, 
            params=params, 
            headers={"Range": range_header}
        )
        
        return OPSResponse(**data)
