import httpx
from typing import Optional, Any, Dict
from .auth import AuthManager
# Import locally to avoid circular dependencies if any, or reorganize
# But here we can import safely if models don't import client (they don't)
# However, api modules import AsyncClient for type hinting.
# To avoid circular imports, we can use TYPE_CHECKING or just import inside __init__

if False: # TYPE_CHECKING
    from .api.search import SearchService
    from .api.retrieval import RetrievalService

class AsyncClient:
    """Async client for EPO OPS API."""
    
    BASE_URL = "https://ops.epo.org/3.2/rest-services"
    
    def __init__(self, consumer_key: str, consumer_secret: str, base_url: str = BASE_URL):
        self.auth = AuthManager(consumer_key, consumer_secret)
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        
        # Initialize services
        from .api.search import SearchService
        from .api.retrieval import RetrievalService
        self.published_data = RetrievalService(self)
        self.search = SearchService(self)

        
    async def __aenter__(self) -> "AsyncClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            
    async def _get_client(self) -> httpx.AsyncClient:
        """Returns the active client or creates a new one temporarily."""
        if self._client:
            return self._client
        return httpx.AsyncClient(timeout=30.0)
        
    async def request(self, method: str, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Makes an authenticated request to the API."""
        endpoint = endpoint.lstrip("/")
        url = f"{self.base_url}/{endpoint}"
        
        # Ensure we have a client instance
        local_client = False
        client = self._client
        if not client:
            client = httpx.AsyncClient(timeout=30.0)
            local_client = True
            
        try:
            token = await self.auth.get_access_token(client)
            
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {token}"
            headers["User-Agent"] = "epopy/0.1.0 (https://github.com/tu-po/epopy)"
            if "Accept" not in headers:
                headers["Accept"] = "application/xml"
            
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        finally:
            if local_client:
                await client.aclose()
    
    async def get_data(self, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Performs a GET request and returns the parsed dictionary (from XML)."""
        import xmltodict
        response = await self.request("GET", endpoint, **kwargs)
        data: Dict[str, Any] = xmltodict.parse(response.text)
        return data

    async def get(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", endpoint, **kwargs)

    async def search_patents(self, q: str, **kwargs: Any) -> Any:
        """
        Search for patents and return high-level Patent objects.
        """
        return await self.search.search_patents(q, **kwargs)

    def get_patent(self, number: str, format: str = "docdb", reference_type: str = "publication") -> Any:
        """
        Get a Patent object for high-level interaction.
        """
        from .patent import Patent
        return Patent(self, number, format=format, type=reference_type)

