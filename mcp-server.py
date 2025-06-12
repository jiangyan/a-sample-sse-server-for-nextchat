import httpx
import asyncio
import click
import os
from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession


class QueuingSession(ServerSession):
    async def _received_request(self, responder):
        # Wait until initialise/notifications is completed
        await self._initialized.wait()
        await super()._received_request(responder)

mcp = FastMCP("My App", session_class=QueuingSession)


@mcp.tool(name="taskmanager.calculate_bmi")
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI given weight in kg and height in meters"""
    return weight_kg / (height_m**2)


@mcp.tool(name="taskmanager.fetch_weather")
async def fetch_weather(city: str) -> str:
    """Fetch current weather for a city"""
    async with httpx.AsyncClient() as client:
        # Using a mock weather API for demo - replace with real API
        response = await client.get(f"https://httpbin.org/json")
        return f"Weather for {city}: Mock weather data - {response.text[:100]}..."


@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="sse",
    help="Transport type",
)
def main(port: int, transport: str):
    """Run the MCP server"""
    if transport == "sse":
        # Set port via environment variable for FastMCP
        os.environ['PORT'] = str(port)
        print(f"Starting MCP server with SSE transport on port {port}")
        asyncio.run(mcp.run_sse_async())
    else:
        # Run as stdio server
        print("Starting MCP server with stdio transport")
        mcp.run()


if __name__ == "__main__":
    main()