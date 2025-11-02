
import pytest
from unittest.mock import patch, AsyncMock
from api.index import get_redis_client

@pytest.mark.asyncio
async def test_redis_connection_logic():
    with patch.dict('os.environ', {
        'UPSTASH_REDIS_URL': 'rediss://:test_token@some-region-1234.upstash.io:12345',
    }):
        with patch('redis.asyncio.from_url') as mock_from_url:
            # Reset redis_client to None to ensure the connection logic is re-run
            with patch('api.index.redis_client', None):
                 get_redis_client()
            expected_url = "rediss://:test_token@some-region-1234.upstash.io:12345"
            mock_from_url.assert_called_with(expected_url, decode_responses=True)
