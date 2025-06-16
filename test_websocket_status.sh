#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testing WebSocket LLM System${NC}"
echo "==============================="
echo

echo "1. Checking Docker services..."
echo

# Check if docker compose is running
if docker compose ps | grep -q "Up"; then
    echo -e "  ${GREEN}✅ Docker Compose services are running${NC}"
else
    echo -e "  ${RED}❌ Docker Compose services are not running${NC}"
    echo "  Please run: docker compose up -d"
    exit 1
fi

echo
echo "2. Checking individual services..."
echo

# Function to check if a port is responding
check_port() {
    local host=$1
    local port=$2
    local name=$3

    if nc -z "$host" "$port" 2>/dev/null; then
        echo -e "  ${GREEN}✅ $name (port $port) - Running${NC}"
        return 0
    else
        echo -e "  ${RED}❌ $name (port $port) - Not responding${NC}"
        return 1
    fi
}

# Check database (we know it might not be used but checking anyway)
check_port localhost 5432 "PostgreSQL Database"

# Check Flask API
check_port localhost 5001 "Flask API Server"

# Check React UI
check_port localhost 3000 "React UI"

echo
echo "3. Checking WebSocket Game Engine Status..."
echo

# Check the new WebSocket Game Engine via port 8100
echo "Checking WebSocket Game Engine via HTTP Status API..."
if curl -s --connect-timeout 5 "http://localhost:8100/status" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ WebSocket Game Engine HTTP API is running${NC}"
    echo
    echo -e "${BLUE}📊 WebSocket Status Details:${NC}"
    echo "============================="
    status_response=$(curl -s "http://localhost:8100/status")
    echo "$status_response" | jq '.' 2>/dev/null || echo "$status_response"
else
    echo -e "${RED}❌ WebSocket Game Engine HTTP API is not responding${NC}"
    echo "  Please check if the websocket service is running:"
    echo "  docker compose logs websocketllm"
fi

echo
echo
echo -e "${BLUE}🎮 Manual Client Startup Commands:${NC}"
echo "================================="
echo
echo "Method 1 - Using the startup script:"
echo "  ./start_llm_clients.sh"
echo "  ./start_llm_clients.sh --players 3  # Start only 3 players"
echo
echo "Method 2 - Start individual clients:"
echo "  # RED Player"
echo "  docker compose exec websocketllm uv run python -m catanatron.multiplayer.llm_agent_client --host websocketllm --port 8001 --color RED --model gemini-1.5-flash"
echo
echo "  # BLUE Player"
echo "  docker compose exec websocketllm uv run python -m catanatron.multiplayer.llm_agent_client --host websocketllm --port 8002 --color BLUE --model gemini-1.5-flash"
echo
echo "  # WHITE Player"
echo "  docker compose exec websocketllm uv run python -m catanatron.multiplayer.llm_agent_client --host websocketllm --port 8003 --color WHITE --model gemini-1.5-flash"
echo
echo "  # ORANGE Player"
echo "  docker compose exec websocketllm uv run python -m catanatron.multiplayer.llm_agent_client --host websocketllm --port 8004 --color ORANGE --model gemini-1.5-flash"

echo
echo -e "${BLUE}📈 Status API Endpoints:${NC}"
echo "======================="
echo "  Direct WebSocket Status: curl http://localhost:8100/status"
echo

echo -e "${BLUE}🔧 Troubleshooting:${NC}"
echo "=================="
echo "• If WebSocket status shows 'not responding', restart with: docker compose restart websocketllm"
echo "• Check WebSocket logs: docker compose logs websocketllm"
echo "• For client connection issues, ensure .env file has valid GOOGLE_API_KEY"
echo
