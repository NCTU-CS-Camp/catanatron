import asyncio
import websockets
import json
import argparse
from typing import Optional

from catanatron.models.player import Color
from catanatron.players.llm import LLMPlayer
from catanatron.json import GameEncoder, action_from_json
from catanatron.game import Game

class LLMAgentClient:
    def __init__(self, server_host: str, server_port: int, color: Color, model_name: str = "gemini-2.5-flash-preview-05-20"):
        self.server_host = server_host
        self.server_port = server_port
        self.color = color
        self.llm_player = LLMPlayer(color, model_name)
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        
    async def connect(self):
        """連接到 Game Engine Server"""
        try:
            uri = f"ws://{self.server_host}:{self.server_port}"
            print(f"Connecting to {uri} as {self.color.value}...")
            
            self.websocket = await websockets.connect(uri)
            self.connected = True
            
            print(f"Connected as {self.color.value} player")
            
            # 發送準備就緒訊息
            await self.send_message({
                'type': 'ready',
                'color': self.color.value
            })
            
            # 開始監聽訊息
            await self.listen_for_messages()
            
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False

    async def listen_for_messages(self):
        """監聽來自服務器的訊息"""
        try:
            async for message in self.websocket:
                await self.handle_message(json.loads(message))
                
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection closed for {self.color.value}")
            self.connected = False
        except Exception as e:
            print(f"Error in message loop: {e}")
            self.connected = False

    async def handle_message(self, data: dict):
        """處理收到的訊息"""
        msg_type = data.get('type')
        
        if msg_type == 'welcome':
            print(f"Received welcome: {data.get('message')}")
            
        elif msg_type == 'game_started':
            print("Game started!")
            
        elif msg_type == 'game_state_update':
            print(f"Game state updated. Current player: {data.get('current_player')}")
            
        elif msg_type == 'action_request':
            await self.handle_action_request(data)
            
        elif msg_type == 'game_end':
            winner = data.get('winner')
            print(f"Game ended! Winner: {winner}")
            if winner == self.color.value:
                print("🎉 We won!")
            else:
                print("😢 We lost...")
            
        elif msg_type == 'error':
            print(f"Error from server: {data.get('message')}")
            
        else:
            print(f"Unknown message type: {msg_type}")

    async def handle_action_request(self, data: dict):
        """處理行動請求"""
        try:
            print(f"\n=== Action Request for {self.color.value} ===")
            
            # 重建遊戲狀態
            game_state_json = data.get('game_state')
            playable_actions_data = data.get('playable_actions', [])
            
            print(f"Available actions: {len(playable_actions_data)}")
            
            # 檢查是否有可用行動
            if not playable_actions_data:
                print("No available actions!")
                print("This might indicate a game state issue.")
                
                # 不發送任何行動，讓服務器處理這種情況
                await self.send_message({
                    'type': 'action',
                    'action': None  # 發送空行動
                })
                return
            
            # 顯示可用行動
            print("Available actions:")
            for i, action_data in enumerate(playable_actions_data):
                print(f"  {i}: {action_data.get('description', action_data.get('action_type'))}")
            
            # 從 JSON 重建遊戲對象
            game = self.reconstruct_game_from_json(game_state_json)
            
            # 使用 LLM 做決策
            chosen_action_index = await self.make_llm_decision(game, playable_actions_data)
            
            if chosen_action_index is not None and 0 <= chosen_action_index < len(playable_actions_data):
                # 發送選擇的行動 - 使用正確的格式
                chosen_action_data = playable_actions_data[chosen_action_index]
                
                # 轉換為 action_from_json 期望的格式: [color, action_type, value]
                action_message = [
                    self.color.value,  # color
                    chosen_action_data['action_type'],  # action_type 
                    chosen_action_data['value']  # value
                ]
                
                await self.send_message({
                    'type': 'action',
                    'action': action_message
                })
                
                print(f"Sent action: {chosen_action_data['description']}")
            else:
                print("Failed to make valid decision, sending first action as fallback")
                # 發送第一個行動作為後備方案
                first_action = playable_actions_data[0]
                action_message = [
                    self.color.value,
                    first_action['action_type'],
                    first_action['value']
                ]
                
                await self.send_message({
                    'type': 'action',
                    'action': action_message
                })
                
        except Exception as e:
            print(f"Error handling action request: {e}")
            import traceback
            traceback.print_exc()
            
            # 作為最後的後備方案，發送空行動
            try:
                await self.send_message({
                    'type': 'action',
                    'action': None
                })
                print("Sent empty action due to error")
            except Exception as fallback_error:
                print(f"Even fallback action failed: {fallback_error}")

    async def make_llm_decision(self, game, playable_actions_data) -> Optional[int]:
        """使用 LLM 做決策"""
        try:
            # 檢查是否有可用行動
            if not playable_actions_data:
                print("No actions available for LLM decision")
                return None
            
            # 創建簡化的 Action 對象列表供 LLM 使用
            from catanatron.models.actions import Action, ActionType
            
            mock_actions = []
            for action_data in playable_actions_data:
                try:
                    action_type = ActionType[action_data['action_type']]
                    action = Action(self.color, action_type, action_data['value'])
                    mock_actions.append(action)
                except Exception as action_error:
                    print(f"Error creating action from {action_data}: {action_error}")
                    # 跳過無法創建的行動
                    continue
            
            if not mock_actions:
                print("No valid actions could be created")
                return 0  # 返回第一個選項
            
            # 簡化：不使用 LLM，直接選擇第一個或隨機選擇
            print(f"LLM decision: choosing action 0 (simplified)")
            return 0
            
            # 如果要使用真正的 LLM，需要創建一個簡化的遊戲對象
            # chosen_action = self.llm_player.decide(game, mock_actions)
            # 
            # if chosen_action:
            #     # 找到對應的索引
            #     for i, action in enumerate(mock_actions):
            #         if (action.action_type == chosen_action.action_type and 
            #             action.value == chosen_action.value):
            #             return i
            # 
            # # 如果找不到匹配的，返回第一個
            # print("LLM decision not found in available actions, using first action")
            # return 0
            
        except Exception as e:
            print(f"Error in LLM decision making: {e}")
            import traceback
            traceback.print_exc()
            return 0  # 默認選擇第一個選項

    def reconstruct_game_from_json(self, game_state_json: str):
        """從 JSON 重建遊戲對象"""
        try:
            # 不需要重建完整的 Game 對象，直接返回 None
            # LLM 玩家可以處理 None 遊戲對象
            return None
            
        except Exception as e:
            print(f"Error reconstructing game from JSON: {e}")
            return None

    async def send_message(self, message: dict):
        """發送訊息給服務器"""
        if self.websocket and self.connected:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                print(f"Error sending message: {e}")
                self.connected = False

    async def disconnect(self):
        """斷開連接"""
        if self.websocket:
            await self.websocket.close()
        self.connected = False

# 命令行啟動
async def main():
    parser = argparse.ArgumentParser(description='LLM Agent Client for Catan')
    parser.add_argument('--host', default='localhost', help='Game server host')
    parser.add_argument('--port', type=int, required=True, help='Game server port')
    parser.add_argument('--color', required=True, choices=['RED', 'BLUE', 'WHITE', 'ORANGE'], 
                       help='Player color')
    parser.add_argument('--model', default='gemini-2.5-flash-preview-05-20', 
                       help='LLM model name')
    
    args = parser.parse_args()
    
    color = Color[args.color]
    client = LLMAgentClient(args.host, args.port, color, args.model)
    
    try:
        await client.connect()
    except KeyboardInterrupt:
        print("\nShutting down client...")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())