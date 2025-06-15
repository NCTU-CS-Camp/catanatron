import asyncio
import websockets
from websockets.legacy.server import WebSocketServerProtocol
import json
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging
import traceback
import argparse

from catanatron.game import Game
from catanatron.models.player import Color, Player
from catanatron.models.actions import Action, generate_playable_actions
from catanatron.json import GameEncoder, action_from_json

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PlayerConnection:
    color: Color
    websocket: WebSocketServerProtocol
    port: int
    connected: bool = True

# 創建一個代理玩家類，用於網路遊戲
class NetworkPlayer(Player):
    """代理玩家，用於網路遊戲中的遠程玩家"""
    def __init__(self, color: Color):
        # 正確初始化 Player 基類
        super().__init__(color=color, is_bot=True)
        logger.info(f"Created NetworkPlayer for {color.value}")
    
    def decide(self, game, playable_actions):
        # 這個方法不會被直接調用，因為決策通過網路處理
        # 返回第一個可用行動作為後備方案
        logger.info(f"NetworkPlayer.decide called for {self.color.value} with {len(playable_actions)} actions")
        return playable_actions[0] if playable_actions else None

class GameEngineServer:
    def __init__(self, host: str = "0.0.0.0", min_players: int = 2, max_players: int = 4):
        self.host = host
        self.base_port = 8001
        self.min_players = min_players  # 最少玩家數量，預設 2
        self.max_players = max_players  # 最多玩家數量，預設 4
        self.player_connections: Dict[Color, PlayerConnection] = {}
        self.game: Optional[Game] = None
        self.game_lock = asyncio.Lock()
        
        # 所有可能的玩家顏色按順序
        self.available_colors = [Color.RED, Color.BLUE, Color.WHITE, Color.ORANGE]
        
        # 根據最大玩家數量設定端口映射
        self.port_color_mapping = {}
        for i in range(min(max_players, len(self.available_colors))):
            self.port_color_mapping[8001 + i] = self.available_colors[i]
        
        # 為每個端口創建服務器
        self.servers: Dict[int, websockets.WebSocketServer] = {}
        
        # 遊戲開始計時器
        self.start_game_timer = None
        self.waiting_time = 30  # 等待 30 秒後自動開始（如果達到最少玩家數）
        
    async def start_all_servers(self):
        """啟動所有端口的 WebSocket 服務器"""
        tasks = []
        for port, color in self.port_color_mapping.items():
            task = asyncio.create_task(self.start_port_server(port, color))
            tasks.append(task)
        
        logger.info(f"Game Engine Server started on {self.host}")
        logger.info("Port assignments:")
        for port, color in self.port_color_mapping.items():
            logger.info(f"  Port {port}: Player {color.value}")
        
        # 等待所有服務器啟動
        await asyncio.gather(*tasks)

    async def start_port_server(self, port: int, color: Color):
        """為特定端口啟動 WebSocket 服務器"""
        async def handler(websocket):
            await self.handle_player_connection(websocket, port, color)
        
        server = await websockets.serve(handler, self.host, port)
        self.servers[port] = server
        logger.info(f"Started server for {color.value} on port {port}")
        
        # 等待服務器運行
        await server.wait_closed()

    async def handle_player_connection(self, websocket, port: int, color: Color):
        """處理玩家連接"""
        # 根據端口確定正確的顏色
        actual_color = self.port_color_mapping.get(port, color)
        logger.info(f"Player {actual_color.value} connected on port {port}")
        
        # 註冊玩家連接
        self.player_connections[actual_color] = PlayerConnection(
            color=actual_color,
            websocket=websocket,
            port=port,
            connected=True
        )
        
        try:
            # 發送歡迎訊息
            await self.send_to_player(actual_color, {
                'type': 'welcome',
                'color': actual_color.value,
                'port': port,
                'message': f'Connected as {actual_color.value} player'
            })
            
            # 檢查是否所有玩家都已連接
            await self.check_all_players_connected()
            
            # 監聽玩家訊息
            async for message in websocket:
                await self.handle_player_message(actual_color, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Player {actual_color.value} disconnected")
        except Exception as e:
            logger.error(f"Error handling player {actual_color.value}: {e}")
            traceback.print_exc()
        finally:
            # 清理連接
            if actual_color in self.player_connections:
                self.player_connections[actual_color].connected = False

    async def handle_player_message(self, color: Color, message: str):
        """處理來自玩家的訊息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'action':
                await self.handle_player_action(color, data.get('action'))
            elif msg_type == 'ready':
                await self.handle_player_ready(color)
            else:
                logger.warning(f"Unknown message type from {color.value}: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from player {color.value}: {message}")
        except Exception as e:
            logger.error(f"Error processing message from {color.value}: {e}")
            traceback.print_exc()

    async def handle_player_action(self, color: Color, action_data):
        """處理玩家行動"""
        async with self.game_lock:
            if not self.game:
                await self.send_to_player(color, {
                    'type': 'error',
                    'message': 'Game not started yet'
                })
                return
            
            # 檢查是否輪到該玩家
            if self.game.state.current_color() != color:
                await self.send_to_player(color, {
                    'type': 'error', 
                    'message': 'Not your turn'
                })
                return
            
            try:
                # 獲取當前可用行動 - 使用正確的屬性
                playable_actions = self.game.state.playable_actions
                
                # 處理特殊的行動類型 - 修正這裡的檢查
                if action_data is None:
                    logger.info(f"Player {color.value} sent empty action")
                    
                    if not playable_actions:
                        logger.warning(f"No actions available for {color.value}, attempting to refresh game state")
                        
                        # 嘗試重新生成可用行動
                        try:
                            fresh_actions = generate_playable_actions(self.game.state)
                            self.game.state.playable_actions = fresh_actions
                            playable_actions = fresh_actions
                            logger.info(f"After refresh: {len(playable_actions)} actions available")
                        except Exception as refresh_error:
                            logger.warning(f"Failed to refresh actions: {refresh_error}")
                        
                        if not playable_actions:
                            await self.send_to_player(color, {
                                'type': 'error',
                                'message': 'No actions available and cannot pass turn'
                            })
                            return
                    
                    # 執行第一個可用行動
                    action = playable_actions[0]
                    logger.info(f"Auto-executing first action for {color.value}: {action}")
                else:
                    # 將 JSON 轉換為 Action 對象
                    # 檢查 action_data 的格式
                    if isinstance(action_data, list) and len(action_data) == 3:
                        # 新格式：["BLUE", "BUILD_SETTLEMENT", 0]
                        try:
                            logger.info(f"Received action data: {action_data}")
                            action = action_from_json(action_data)
                            logger.info(f"Parsed action: {action}")
                        except Exception as action_error:
                            logger.error(f"Error creating action from list: {action_error}")
                            logger.error(f"Action data: {action_data}")
                            await self.send_to_player(color, {
                                'type': 'error',
                                'message': f'Invalid action format: {action_error}'
                            })
                            return
                    elif isinstance(action_data, dict) and 'action_type' in action_data:
                        # 字典格式：{'action_type': 'BUILD_SETTLEMENT', 'value': 0}
                        try:
                            from catanatron.models.actions import ActionType
                            action_type = ActionType[action_data['action_type']]
                            action = Action(color, action_type, action_data['value'])
                        except Exception as action_error:
                            logger.error(f"Error creating action from dict: {action_error}")
                            logger.error(f"Action data: {action_data}")
                            await self.send_to_player(color, {
                                'type': 'error',
                                'message': f'Invalid action format: {action_error}'
                            })
                            return
                    else:
                        # 未知格式
                        logger.error(f"Unknown action data format: {action_data} (type: {type(action_data)})")
                        await self.send_to_player(color, {
                            'type': 'error',
                            'message': f'Unknown action format. Expected list or dict, got {type(action_data)}'
                        })
                        return
                
                # 驗證行動是否有效
                if not playable_actions:
                    logger.error(f"No playable actions available for {color.value}")
                    logger.error(f"Game state details:")
                    logger.error(f"  Current player: {self.game.state.current_color()}")
                    logger.error(f"  Current prompt: {self.game.state.current_prompt}")
                    logger.error(f"  Turn number: {self.game.state.num_turns}")
                    
                    await self.send_to_player(color, {
                        'type': 'error',
                        'message': 'No actions available'
                    })
                    return
                
                if action not in playable_actions:
                    logger.warning(f"Invalid action from {color.value}: {action}")
                    logger.info(f"Available actions: {[str(a) for a in playable_actions[:5]]}...")
                    await self.send_to_player(color, {
                        'type': 'error',
                        'message': 'Invalid action'
                    })
                    return
                
                # 執行行動
                self.game.execute(action)
                logger.info(f"Player {color.value} executed action: {action}")
                
                # 廣播遊戲狀態更新
                await self.broadcast_game_state()
                
                # 檢查遊戲是否結束
                winner = self.game.winning_color()
                if winner:
                    await self.broadcast_game_end(winner)
                else:
                    # 請求下一個玩家行動
                    await self.request_next_player_action()
                    
            except Exception as e:
                logger.error(f"Error executing action from {color.value}: {e}")
                traceback.print_exc()
                await self.send_to_player(color, {
                    'type': 'error',
                    'message': f'Action execution failed: {str(e)}'
                })

    async def handle_player_ready(self, color: Color):
        """處理玩家準備就緒"""
        logger.info(f"Player {color.value} is ready")

    async def check_all_players_connected(self):
        """檢查是否所有玩家都已連接"""
        connected_players = [
            conn for conn in self.player_connections.values() 
            if conn.connected
        ]
        
        connected_count = len(connected_players)
        
        if connected_count >= self.max_players:
            # 達到最大玩家數，立即開始遊戲
            logger.info(f"Maximum {self.max_players} players connected! Starting game immediately...")
            if self.start_game_timer:
                self.start_game_timer.cancel()
                self.start_game_timer = None
            await self.start_game()
        elif connected_count >= self.min_players:
            # 達到最少玩家數，開始倒數計時
            if not self.start_game_timer:
                logger.info(f"{connected_count} players connected (min: {self.min_players}, max: {self.max_players})")
                logger.info(f"Game will start in {self.waiting_time} seconds, or when max players join...")
                
                # 廣播等待訊息給所有玩家
                await self.broadcast_to_all({
                    'type': 'waiting_for_players',
                    'message': f'Waiting for more players... Game will start in {self.waiting_time} seconds',
                    'current_players': connected_count,
                    'min_players': self.min_players,
                    'max_players': self.max_players,
                    'countdown': self.waiting_time
                })
                
                # 設定計時器
                self.start_game_timer = asyncio.create_task(self._start_game_after_delay())
        else:
            # 玩家數量不足
            logger.info(f"Only {connected_count} players connected. Need at least {self.min_players} players.")
            await self.broadcast_to_all({
                'type': 'waiting_for_players',
                'message': f'Waiting for players... ({connected_count}/{self.min_players} minimum)',
                'current_players': connected_count,
                'min_players': self.min_players,
                'max_players': self.max_players
            })

    async def _start_game_after_delay(self):
        """延遲後開始遊戲"""
        try:
            await asyncio.sleep(self.waiting_time)
            connected_count = len([
                conn for conn in self.player_connections.values() 
                if conn.connected
            ])
            
            if connected_count >= self.min_players:
                logger.info(f"Starting game with {connected_count} players after waiting period...")
                await self.start_game()
            else:
                logger.info(f"Not enough players to start game ({connected_count}/{self.min_players})")
        except asyncio.CancelledError:
            logger.info("Game start timer cancelled")
        finally:
            self.start_game_timer = None

    async def start_game(self):
        """開始遊戲"""
        async with self.game_lock:
            if self.game is not None:
                return  # 遊戲已經開始
            
            try:
                # 取得實際連接的玩家
                connected_players = [
                    conn for conn in self.player_connections.values() 
                    if conn.connected
                ]
                
                if len(connected_players) < self.min_players:
                    logger.error(f"Not enough players to start game: {len(connected_players)}/{self.min_players}")
                    return
                
                # 根據連接的玩家創建對應顏色的 NetworkPlayer
                players = []
                for conn in connected_players:
                    players.append(NetworkPlayer(conn.color))
                
                # 按照顏色順序排序玩家（確保遊戲順序一致）
                color_order = [Color.RED, Color.BLUE, Color.WHITE, Color.ORANGE]
                players.sort(key=lambda p: color_order.index(p.color))
                
                logger.info(f"Creating game with {len(players)} players")
                for p in players:
                    logger.info(f"  Player: {p.color.value}, is_bot: {p.is_bot}")
                
                # 使用正確的參數創建遊戲實例
                self.game = Game(
                    players=players,
                    seed=None,  # 隨機種子
                    discard_limit=7,
                    vps_to_win=10,
                    catan_map=None,  # 使用默認地圖
                    initialize=True  # 初始化遊戲
                )
                
                logger.info("Game created successfully!")
                
                # 檢查初始遊戲狀態 - 使用正確的屬性
                current_color = self.game.state.current_color()
                playable_actions = self.game.state.playable_actions  # 使用正確的屬性
                logger.info(f"Initial game state:")
                logger.info(f"  Current player: {current_color.value}")
                logger.info(f"  Actions available: {len(playable_actions)}")
                logger.info(f"  Current prompt: {self.game.state.current_prompt}")
                logger.info(f"  Turn number: {self.game.state.num_turns}")
                logger.info(f"  Is initial build phase: {self.game.state.is_initial_build_phase}")
                
                # 如果沒有行動，嘗試手動刷新
                if not playable_actions:
                    logger.warning("No actions available at game start! Attempting manual refresh...")
                    
                    try:
                        # 使用正確的函數重新計算行動
                        fresh_actions = generate_playable_actions(self.game.state)
                        logger.info(f"Manual action calculation found {len(fresh_actions)} actions")
                        
                        if fresh_actions:
                            self.game.state.playable_actions = fresh_actions
                            playable_actions = fresh_actions
                            logger.info("Successfully refreshed actions")
                            
                            # 顯示一些示例行動
                            for i, action in enumerate(fresh_actions[:5]):
                                logger.info(f"  Action {i}: {action}")
                        
                    except Exception as refresh_error:
                        logger.error(f"Error trying to refresh actions: {refresh_error}")
                        traceback.print_exc()
                
                if playable_actions:
                    logger.info(f"Sample actions: {[str(a) for a in playable_actions[:3]]}")
                else:
                    logger.error("Still no actions available after refresh attempts")
                    
            except Exception as e:
                logger.error(f"Failed to create game: {e}")
                traceback.print_exc()
                return
            
            logger.info(f"Game started with {len(self.game.state.players)} players!")
            
            # 廣播遊戲開始
            await self.broadcast_to_all({
                'type': 'game_started',
                'message': f'Game has started with {len(self.game.state.players)} players!',
                'player_count': len(self.game.state.players),
                'debug_info': {
                    'current_player': self.game.state.current_color().value,
                    'current_prompt': str(self.game.state.current_prompt),
                    'actions_count': len(self.game.state.playable_actions)
                }
            })
            
            # 廣播初始遊戲狀態
            await self.broadcast_game_state()
            
            # 請求第一個玩家行動
            await self.request_next_player_action()

    async def request_next_player_action(self):
        """請求下一個玩家的行動"""
        if not self.game:
            return
            
        try:
            current_color = self.game.state.current_color()
            playable_actions = self.game.state.playable_actions  # 使用正確的屬性
            
            logger.info(f"Requesting action from {current_color.value}, {len(playable_actions)} actions available")
            
            # 如果沒有可用行動，記錄詳細信息
            if not playable_actions:
                logger.error(f"No actions available for {current_color.value}!")
                logger.error(f"Game state: turn {self.game.state.num_turns}, current_prompt: {self.game.state.current_prompt}")
                
                # 嘗試刷新行動
                try:
                    fresh_actions = generate_playable_actions(self.game.state)
                    if fresh_actions:
                        self.game.state.playable_actions = fresh_actions
                        playable_actions = fresh_actions
                        logger.info(f"Successfully refreshed {len(fresh_actions)} actions")
                except Exception as refresh_error:
                    logger.error(f"Failed to refresh actions: {refresh_error}")
                
                if not playable_actions:
                    # 嘗試診斷問題
                    await self.send_to_player(current_color, {
                        'type': 'error',
                        'message': 'No actions available in current game state',
                        'debug_info': {
                            'current_prompt': str(self.game.state.current_prompt),
                            'turn_number': self.game.state.num_turns,
                            'current_player': current_color.value
                        }
                    })
                    return
            
            # 序列化可用行動 - 確保所有值都是 JSON 可序列化的
            actions_data = []
            for i, action in enumerate(playable_actions):
                try:
                    # 確保 action.value 是可序列化的
                    action_value = action.value
                    
                    # 處理特殊的值類型
                    if hasattr(action_value, '__iter__') and not isinstance(action_value, (str, bytes)):
                        # 處理元組、列表等可迭代對象
                        try:
                            # 嘗試轉換為列表，並處理其中的特殊對象
                            action_value = list(action_value)
                            # 轉換其中的 Color 對象為字符串
                            for j, item in enumerate(action_value):
                                if hasattr(item, 'value') and hasattr(item, 'name'):  # Color 枚舉
                                    action_value[j] = item.value
                                elif hasattr(item, 'name'):  # 其他枚舉
                                    action_value[j] = item.name
                                elif item is None:
                                    action_value[j] = None
                        except Exception:
                            # 如果轉換失敗，使用字符串表示
                            action_value = str(action_value)
                    elif hasattr(action_value, 'value') and hasattr(action_value, 'name'):  # Color 枚舉
                        action_value = action_value.value
                    elif hasattr(action_value, 'name'):  # 其他枚舉
                        action_value = action_value.name
                    
                    actions_data.append({
                        'index': i,
                        'action_type': action.action_type.name,
                        'value': action_value,
                        'description': str(action)
                    })
                except Exception as serialize_error:
                    logger.warning(f"Error serializing action {i}: {serialize_error}")
                    # 使用簡化版本
                    actions_data.append({
                        'index': i,
                        'action_type': action.action_type.name,
                        'value': str(action.value),
                        'description': str(action)
                    })
            
            # 向當前玩家請求行動
            await self.send_to_player(current_color, {
                'type': 'action_request',
                'playable_actions': actions_data,
                'game_state': json.dumps(self.game, cls=GameEncoder),
                'debug_info': {
                    'current_prompt': str(self.game.state.current_prompt),
                    'turn_number': self.game.state.num_turns
                }
            })
            
            logger.info(f"Requested action from player {current_color.value}")
        except Exception as e:
            logger.error(f"Error requesting next player action: {e}")
            traceback.print_exc()

    async def broadcast_game_state(self):
        """廣播遊戲狀態給所有玩家"""
        if not self.game:
            return
            
        try:
            game_state_json = json.dumps(self.game, cls=GameEncoder)
            message = {
                'type': 'game_state_update',
                'game_state': game_state_json,
                'current_player': self.game.state.current_color().value,
                'debug_info': {
                    'current_prompt': str(self.game.state.current_prompt),
                    'actions_count': len(self.game.state.playable_actions)
                }
            }
            
            await self.broadcast_to_all(message)
        except Exception as e:
            logger.error(f"Error broadcasting game state: {e}")
            traceback.print_exc()

    async def broadcast_game_end(self, winner: Color):
        """廣播遊戲結束"""
        message = {
            'type': 'game_end',
            'winner': winner.value,
            'message': f'Player {winner.value} wins!'
        }
        
        await self.broadcast_to_all(message)
        logger.info(f"Game ended! Winner: {winner.value}")

    async def send_to_player(self, color: Color, message: dict):
        """發送訊息給特定玩家"""
        if color not in self.player_connections:
            logger.warning(f"Player {color.value} not connected")
            return
            
        connection = self.player_connections[color]
        if not connection.connected:
            logger.warning(f"Player {color.value} connection closed")
            return
            
        try:
            await connection.websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Failed to send message to {color.value}: connection closed")
            connection.connected = False
        except Exception as e:
            logger.error(f"Error sending message to {color.value}: {e}")

    async def broadcast_to_all(self, message: dict):
        """廣播訊息給所有玩家"""
        for color in self.player_connections:
            await self.send_to_player(color, message)

# 啟動服務器
async def main():
    """主函數，支援命令列參數設定玩家數量"""
    parser = argparse.ArgumentParser(description='Catanatron 多人遊戲伺服器')
    parser.add_argument('--min-players', type=int, default=2, 
                       help='最少玩家數量 (預設: 2)')
    parser.add_argument('--max-players', type=int, default=4, 
                       help='最多玩家數量 (預設: 4)')
    parser.add_argument('--wait-time', type=int, default=30,
                       help='達到最少玩家數後等待時間(秒) (預設: 30)')
    parser.add_argument('--host', type=str, default="0.0.0.0",
                       help='伺服器主機地址 (預設: 0.0.0.0)')
    
    args = parser.parse_args()
    
    # 驗證參數
    if args.min_players < 2:
        print("錯誤：最少玩家數量必須至少為 2")
        return
    if args.max_players > 4:
        print("錯誤：最多玩家數量不能超過 4 (顏色限制)")
        return
    if args.min_players > args.max_players:
        print("錯誤：最少玩家數量不能大於最多玩家數量")
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    Catanatron 多人遊戲伺服器                    ║
╠══════════════════════════════════════════════════════════════╣
║  設定:                                                        ║
║    最少玩家數量: {args.min_players:<2}                                           ║
║    最多玩家數量: {args.max_players:<2}                                           ║
║    等待時間: {args.wait_time:<3} 秒                                        ║
║    主機地址: {args.host:<15}                                    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    server = GameEngineServer(
        host=args.host,
        min_players=args.min_players, 
        max_players=args.max_players
    )
    
    # 設定等待時間
    server.waiting_time = args.wait_time
    
    print("正在啟動伺服器...")
    print(f"玩家可以連接到以下端口:")
    
    colors = ["RED", "BLUE", "WHITE", "ORANGE"]
    for i in range(args.max_players):
        port = 8001 + i
        color = colors[i]
        print(f"  端口 {port}: {color} 玩家")
    
    print(f"\n遊戲規則:")
    print(f"  - 至少需要 {args.min_players} 個玩家才能開始遊戲")
    print(f"  - 最多支援 {args.max_players} 個玩家")
    print(f"  - 達到最少玩家數後，等待 {args.wait_time} 秒或直到滿員")
    print(f"  - 玩家可以隨時加入，直到達到最大數量\n")
    
    try:
        await server.start_all_servers()
    except KeyboardInterrupt:
        print("\n正在關閉伺服器...")
        for server_instance in server.servers.values():
            server_instance.close()
            await server_instance.wait_closed()
        print("伺服器已關閉")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")