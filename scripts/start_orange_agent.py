#!/usr/bin/env python3
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'catanatron'))

from catanatron.multiplayer.llm_agent_client import LLMAgentClient
from catanatron.models.player import Color

async def main():
    client = LLMAgentClient(
        server_host="localhost",
        server_port=8004,
        color=Color.ORANGE,
        model_name="gemini-1.5-flash"
    )
    
    print("Starting ORANGE LLM Agent...")
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())