from __future__ import annotations

from fastmcp import FastMCP


mcp = FastMCP(name="agentbreak-example-mcp", version="0.1.0")


@mcp.tool(name="echo_text", description="Echo the provided text back to the caller.")
def echo_text(text: str) -> str:
    return f"echo: {text}"


@mcp.tool(name="add_numbers", description="Add two integers and return the result.")
def add_numbers(a: int, b: int) -> dict[str, int]:
    return {"result": a + b}


@mcp.tool(name="get_weather", description="Return mock weather data for a city.")
def get_weather(city: str) -> dict[str, str]:
    return {
        "city": city,
        "forecast": "warm and clear",
    }


def main() -> None:
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001, path="/mcp")


if __name__ == "__main__":
    main()
