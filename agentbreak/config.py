from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class AuthConfig(BaseModel):
    type: Literal["none", "bearer", "basic", "header", "oauth2_client_credentials"] = "none"
    # bearer: token from env var or inline
    env: str | None = None
    token: str | None = None
    # basic: username + password from env var
    username: str | None = None
    password_env: str | None = None
    # header: arbitrary header name + value from env var
    header_name: str | None = None
    header_value_env: str | None = None
    # oauth2_client_credentials
    token_url: str | None = None
    client_id: str | None = None
    client_secret_env: str | None = None
    scopes: list[str] = Field(default_factory=list)

    # Internal token cache (excluded from serialization)
    _cached_token: str | None = None
    _token_expiry: float = 0.0

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _check_required_fields(self) -> "AuthConfig":
        if self.type == "bearer":
            if not self.env and not self.token:
                raise ValueError("bearer auth requires 'env' or 'token'")
        elif self.type == "basic":
            if not self.username:
                raise ValueError("basic auth requires 'username'")
            if not self.password_env:
                raise ValueError("basic auth requires 'password_env'")
        elif self.type == "header":
            if not self.header_name:
                raise ValueError("header auth requires 'header_name'")
            if not self.header_value_env:
                raise ValueError("header auth requires 'header_value_env'")
        elif self.type == "oauth2_client_credentials":
            if not self.token_url:
                raise ValueError("oauth2_client_credentials auth requires 'token_url'")
            if not self.client_id:
                raise ValueError("oauth2_client_credentials auth requires 'client_id'")
            if not self.client_secret_env:
                raise ValueError("oauth2_client_credentials auth requires 'client_secret_env'")
        return self

    def _fetch_oauth2_token(self) -> str | None:
        """Fetch an OAuth2 token using client_credentials grant, with caching."""
        now = time.time()
        if self._cached_token and now < self._token_expiry:
            return self._cached_token

        import httpx

        client_secret = os.getenv(self.client_secret_env) if self.client_secret_env else None
        if not client_secret:
            return None

        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self.client_id or "",
            "client_secret": client_secret,
        }
        if self.scopes:
            data["scope"] = " ".join(self.scopes)

        resp = httpx.post(self.token_url or "", data=data, timeout=30.0)
        resp.raise_for_status()
        body = resp.json()

        access_token: str = body.get("access_token", "")
        expires_in: int = int(body.get("expires_in", 3600))
        # Refresh 60s before actual expiry to avoid edge-case failures
        self._cached_token = access_token
        self._token_expiry = now + max(expires_in - 60, 0)
        return access_token

    def headers(self) -> dict[str, str]:
        if self.type == "none":
            return {}

        if self.type == "bearer":
            token = self.token or (os.getenv(self.env) if self.env else None)
            if not token:
                return {}
            return {"authorization": f"Bearer {token}"}

        if self.type == "basic":
            password = os.getenv(self.password_env) if self.password_env else None
            if not password:
                return {}
            credentials = base64.b64encode(
                f"{self.username}:{password}".encode()
            ).decode()
            return {"authorization": f"Basic {credentials}"}

        if self.type == "header":
            value = os.getenv(self.header_value_env) if self.header_value_env else None
            if not value:
                return {}
            return {self.header_name or "": value}

        if self.type == "oauth2_client_credentials":
            token = self._fetch_oauth2_token()
            if not token:
                return {}
            return {"authorization": f"Bearer {token}"}

        return {}


class UpstreamConfig(BaseModel):
    name: str
    url: str
    api_key_env: str | None = None
    auth: AuthConfig = Field(default_factory=AuthConfig)


class LLMConfig(BaseModel):
    enabled: bool = True
    upstream_url: str = ""  # kept for backward compat
    mode: Literal["proxy", "mock"] = "mock"
    auth: AuthConfig = Field(default_factory=AuthConfig)
    upstreams: list[UpstreamConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def _backfill_upstreams(self) -> "LLMConfig":
        if not self.upstreams and self.upstream_url:
            self.upstreams = [
                UpstreamConfig(
                    name="default",
                    url=self.upstream_url,
                    auth=self.auth,
                )
            ]
        return self


class MCPConfig(BaseModel):
    enabled: bool = False
    upstream_url: str = ""
    transport: Literal["streamable_http"] = "streamable_http"
    auth: AuthConfig = Field(default_factory=AuthConfig)


class ServeConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 5000


class HistoryConfig(BaseModel):
    enabled: bool = False
    db_path: str = ".agentbreak/history.db"


class ApplicationConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    serve: ServeConfig = Field(default_factory=ServeConfig)
    history: HistoryConfig = Field(default_factory=HistoryConfig)

    @model_validator(mode="after")
    def validate_modes(self) -> "ApplicationConfig":
        if self.llm.enabled and self.llm.mode == "proxy":
            if not self.llm.upstream_url and not self.llm.upstreams:
                raise ValueError("llm.upstream_url or llm.upstreams is required when llm.mode is 'proxy'")
        return self


class MCPTool(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")

    model_config = {"populate_by_name": True}


class MCPResource(BaseModel):
    uri: str
    name: str = ""
    description: str = ""
    mime_type: str = Field(default="", alias="mimeType")

    model_config = {"populate_by_name": True}


class MCPPrompt(BaseModel):
    name: str
    description: str = ""
    arguments: list[dict[str, Any]] = Field(default_factory=list)


class MCPRegistry(BaseModel):
    version: int = 1
    tools: list[MCPTool] = Field(default_factory=list)
    resources: list[MCPResource] = Field(default_factory=list)
    prompts: list[MCPPrompt] = Field(default_factory=list)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a top-level mapping")
    return data


def load_application_config(path: str | None) -> ApplicationConfig:
    candidate = Path(path) if path else Path("application.yaml")
    if not candidate.exists():
        raise FileNotFoundError(f"Config file not found: {candidate}")
    return ApplicationConfig.model_validate(_load_yaml_mapping(candidate))


def load_registry(path: str | None) -> MCPRegistry:
    candidate = Path(path) if path else Path(".agentbreak/registry.json")
    if not candidate.exists():
        raise ValueError(f"MCP registry not found: {candidate}")
    with candidate.open("r", encoding="utf-8") as handle:
        return MCPRegistry.model_validate(json.load(handle))


def save_registry(registry: MCPRegistry, path: str | None) -> Path:
    candidate = Path(path) if path else Path(".agentbreak/registry.json")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(json.dumps(registry.model_dump(by_alias=True), indent=2), encoding="utf-8")
    return candidate
