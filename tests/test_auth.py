import pytest

import time
from httpx import Response
from epopy.auth import AuthManager

from typing import Any

@pytest.mark.asyncio
async def test_get_access_token_success(respx_mock: Any) -> None:
    respx_mock.post("https://ops.epo.org/3.2/auth/accesstoken").mock(
        return_value=Response(
            200, 
            json={"access_token": "new_token", "expires_in": "600"}
        )
    )
    
    auth = AuthManager("key", "secret")
    token = await auth.get_access_token()
    
    assert token == "new_token"
    assert auth._access_token == "new_token" # type: ignore

@pytest.mark.asyncio
async def test_token_caching(respx_mock: Any) -> None:
    # Only one request should be made
    route = respx_mock.post("https://ops.epo.org/3.2/auth/accesstoken").mock(
        return_value=Response(
            200, 
            json={"access_token": "cached_token", "expires_in": "600"}
        )
    )
    
    auth = AuthManager("key", "secret")
    token1 = await auth.get_access_token()
    token2 = await auth.get_access_token()
    
    assert token1 == token2 == "cached_token"
    assert route.call_count == 1

@pytest.mark.asyncio
async def test_token_expiration(respx_mock: Any) -> None:
    route = respx_mock.post("https://ops.epo.org/3.2/auth/accesstoken").mock(
        return_value=Response(
            200, 
            json={"access_token": "token", "expires_in": "1"} # 1 second expiry
        )
    )
    
    auth = AuthManager("key", "secret")
    await auth.get_access_token()
    
    # Simulate expiration
    auth._token_expires_at = time.time() - 10 # type: ignore
    
    await auth.get_access_token()
    assert route.call_count == 2
