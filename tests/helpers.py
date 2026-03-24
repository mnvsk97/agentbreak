from __future__ import annotations


class DummyResponse:
    def __init__(
        self,
        status_code: int = 200,
        content: bytes = b'{"ok":true}',
        headers: dict[str, str] | None = None,
        json_data: dict | None = None,
    ):
        self.status_code = status_code
        self.content = content if json_data is None else __import__("json").dumps(json_data).encode("utf-8")
        self.headers = headers or {"content-type": "application/json"}
        self._json_data = json_data

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self):
        if self._json_data is not None:
            return self._json_data
        return __import__("json").loads(self.content.decode("utf-8"))

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

class DummyAsyncClient:
    response = DummyResponse()
    responses: list[DummyResponse] = []
    error: Exception | None = None
    calls: list[dict] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> "DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, content: bytes | None = None, headers: dict[str, str] | None = None, json=None):
        DummyAsyncClient.calls.append({"url": url, "content": content, "headers": headers or {}, "json": json})
        if DummyAsyncClient.error is not None:
            raise DummyAsyncClient.error
        if DummyAsyncClient.responses:
            return DummyAsyncClient.responses.pop(0)
        return DummyAsyncClient.response
