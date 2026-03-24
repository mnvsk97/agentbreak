import os

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


@tool
def get_weather(city: str) -> str:
    """Return fake weather for a city."""
    return f"The weather in {city} is warm and clear."


def load_request_count() -> int:
    raw = os.getenv("AGENTBREAK_REQUEST_COUNT")
    return max(1, int(raw)) if raw is not None else 1


def main() -> None:
    request_count = load_request_count()
    model = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:5000/v1"),
    )
    agent = create_agent(
        model=model,
        tools=[get_weather],
        system_prompt="You are concise. Use tools when useful.",
    )
    for index in range(1, request_count + 1):
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "What's the weather in San Francisco? Answer in one sentence.",
                    }
                ]
            }
        )
        print(f"[{index}/{request_count}] {result['messages'][-1].content}")


if __name__ == "__main__":
    main()
