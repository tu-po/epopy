import pytest

from typing import AsyncGenerator, Any
from httpx import Response
from epopy import AsyncClient

import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
def consumer_key() -> str:
    return os.getenv("EPO_CONSUMER_KEY", "fake_key")

@pytest.fixture
def consumer_secret() -> str:
    return os.getenv("EPO_CONSUMER_SECRET", "fake_secret")

@pytest.fixture
async def client(consumer_key: str, consumer_secret: str) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(consumer_key, consumer_secret) as c:
        yield c

@pytest.fixture
def mock_token(respx_mock: Any) -> None:
    respx_mock.post("https://ops.epo.org/3.2/auth/accesstoken").mock(
        return_value=Response(
            200, 
            json={
                "access_token": "mock_token", 
                "expires_in": 1200, 
                "token_type": "bearer"
            }
        )
    )
