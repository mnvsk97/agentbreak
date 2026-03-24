from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class AuthConfig(BaseModel):
    type: Literal["none", "bearer"] = "none"
    env: str | None = None
    token: str | None = None

    def headers(self) -> dict[str, str]:
        if self.type == "none":
            return {}
        token = self.token or (os.getenv(self.env) if self.env else None)
        if not token:
            return {}
        return {"authorization": f"Bearer {token}"}


class LLMConfig(BaseModel):
    enabled: bool = True
    upstream_url: str = ""
    mode: Literal["proxy", "mock"] = "mock"
    auth: AuthConfig = Field(default_factory=AuthConfig)


class MCPConfig(BaseModel):
    enabled: bool = False
    upstream_url: str = ""
    transport: Literal["streamable_http"] = "streamable_http"
    auth: AuthConfig = Field(default_factory=AuthConfig)


class ServeConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 5000


class ApplicationConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    serve: ServeConfig = Field(default_factory=ServeConfig)

    @model_validator(mode="after")
    def validate_modes(self) -> "ApplicationConfig":
        if self.llm.enabled and self.llm.mode == "proxy" and not self.llm.upstream_url:
            raise ValueError("llm.upstream_url is required when llm.mode is 'proxy'")
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
