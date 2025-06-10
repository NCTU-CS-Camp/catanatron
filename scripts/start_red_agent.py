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
        server_port=8001,
        color=Color.RED,
        model_name="gemini-2.5-flash-preview-05-20"
    )
    
    print("Starting RED LLM Agent...")
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())