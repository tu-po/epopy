import time
import base64
import httpx
from typing import Optional

class AuthManager:
    """Handles OAuth 2.0 authentication for EPO OPS API."""
    
    TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"
    
    def __init__(self, consumer_key: str, consumer_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        
    @property
    def _auth_header(self) -> str:
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
        
    async def get_access_token(self, client: Optional[httpx.AsyncClient] = None) -> str:
        """Returns a valid access token, refreshing if necessary."""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token
            
        return await self._refresh_token(client)
        
    async def _refresh_token(self, client: Optional[httpx.AsyncClient] = None) -> str:
        """Refreshes the access token using the client credentials flow."""
        headers = {
            "Authorization": self._auth_header,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        
        # Use provided client or create a new one for the auth request
        if client:
            response = await client.post(self.TOKEN_URL, headers=headers, data=data)
        else:
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.post(self.TOKEN_URL, headers=headers, data=data)
                
        response.raise_for_status()
        token_data = response.json()
        
        token = str(token_data["access_token"])
        self._access_token = token
        
        # Default expiration is usually 20 minutes (1200 seconds), but we use the returned expires_in if available
        expires_in = int(token_data.get("expires_in", 1200))
        self._token_expires_at = time.time() + expires_in
        
        return token
