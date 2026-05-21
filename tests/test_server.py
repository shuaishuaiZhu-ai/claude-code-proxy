import json
import threading
import unittest
import urllib.request

from ccproxy.config import ProviderProfile, ServerConfig
from ccproxy.server import build_stdlib_server


class ServerTests(unittest.TestCase):
    def test_health_allows_query_string(self) -> None:
        profile = ProviderProfile(
            name="mock",
            type="openai-compatible",
            base_url="http://127.0.0.1:1/v1",
            api_key_env="MOCK_API_KEY",
            models={"big": "mock-model"},
        )
        server = build_stdlib_server(ServerConfig(port=0), profile)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health?ready=1", timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["profile"], "mock")
            self.assertTrue(payload["ok"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
