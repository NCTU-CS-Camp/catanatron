#!/usr/bin/env python3
"""
啟動 Game Engine Server 的腳本
"""
import asyncio
import sys
import os

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'catanatron'))

from catanatron.multiplayer.game_engine_server import GameEngineServer

async def main():
    server = GameEngineServer(host="0.0.0.0")
    print("Starting Catanatron Game Engine Server...")
    print("Listening on:")
    print("  Port 8001: RED player")
    print("  Port 8002: BLUE player") 
    print("  Port 8003: WHITE player")
    print("  Port 8004: ORANGE player")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        await server.start_all_servers()
    except KeyboardInterrupt:
        print("\nShutting down server...")

if __name__ == "__main__":
    asyncio.run(main())