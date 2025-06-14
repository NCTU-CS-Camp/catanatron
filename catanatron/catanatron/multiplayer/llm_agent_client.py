import asyncio
import websockets
import json
import argparse
from typing import Optional, Dict, Tuple
import time
from collections import defaultdict, deque

from catanatron.models.player import Color
from catanatron.players.llm import LLMPlayer
from catanatron.json import GameEncoder, action_from_json
from catanatron.game import Game

class LLMAgentClient:
    def __init__(self, server_host: str, server_port: int, color: Color, model_name: str = "gemini-1.5-flash"):
        self.server_host = server_host
        self.server_port = server_port
        self.color = color
        self.model_name = model_name
        self.websocket = None
        self.connected = False
        self.last_api_call = 0
        self.min_interval = 3  # 減少到3秒間隔以加快調試
        
        # 🔧 修复：添加缺失的属性初始化
        self.action_count = 0  # 行动计数器
        self.current_turn = 0  # 回合追蹤
        self.previous_resources = {}  # 资源追踪
        self.debug_mode = False  # 调试模式
        
        # 🔧 简化：删除详细的交易追蹤
        # self.trade_proposals_count = defaultdict(int)  # 删除
        # self.max_trades_per_player = 3  # 删除
        
        # 建立 LLM 玩家實例
        try:
            from catanatron.players.llm import LLMPlayer
            self.llm_player = LLMPlayer(color, model_name)
            print(f"✅ Created LLM player for {color.value} using {model_name}")
        except Exception as e:
            print(f"⚠️ Failed to create LLM player: {e}")
            self.llm_player = None

    async def connect(self):
        """連接到 Game Engine Server"""
        try:
            uri = f"ws://{self.server_host}:{self.server_port}"
            print(f"🔗 Connecting to {uri} as {self.color.value}...")
            
            self.websocket = await websockets.connect(uri)
            self.connected = True
            
            print(f"✅ Connected as {self.color.value} player")
            
            # 發送準備就緒訊息
            await self.send_message({
                'type': 'ready',
                'color': self.color.value
            })
            
            # 開始監聽訊息
            await self.listen_for_messages()
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.connected = False

    async def listen_for_messages(self):
        """監聽來自服務器的訊息"""
        try:
            async for message in self.websocket:
                await self.handle_message(json.loads(message))
                
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Connection closed for {self.color.value}")
            self.connected = False
        except Exception as e:
            print(f"❌ Error in message loop: {e}")
            self.connected = False

    async def handle_message(self, data: dict):
        """處理收到的訊息"""
        msg_type = data.get('type')
        
        if msg_type == 'welcome':
            print(f"👋 Received welcome: {data.get('message')}")
            
        elif msg_type == 'game_started':
            print(f"🎮 Game started!")
            # 🆕 初始化资源追踪
            await self.initialize_resource_tracking(data)
            
        elif msg_type == 'game_state_update':
            current_player = data.get('current_player')
            is_my_turn = current_player == self.color.value
            turn_indicator = "🔥 MY TURN" if is_my_turn else f"⏳ {current_player}'s turn"
            print(f"📊 Game state updated. {turn_indicator}")
            
            # 🆕 检查资源变动
            await self.check_resource_changes(data)
            
            # 🔧 檢測新回合並重置交易計數
            debug_info = data.get('debug_info', {})
            turn_number = debug_info.get('turn_number', 0)
            if turn_number > self.current_turn:
                self.current_turn = turn_number
                # 每隔幾回合重置交易計數（可選）
                if turn_number % 10 == 0:  # 每10回合重置一次
                    old_count = len(self.trade_proposals_count)
                    self.trade_proposals_count.clear()
                    print(f"🔄 Reset trade proposals count (was tracking {old_count} players)")
            
        elif msg_type == 'action_request':
            await self.handle_action_request(data)
            
        elif msg_type == 'game_end':
            winner = data.get('winner')
            print(f"🏁 Game ended! Winner: {winner}")
            if winner == self.color.value:
                print("🎉 WE WON!")
            else:
                print("😢 We lost...")
            
        elif msg_type == 'error':
            print(f"❌ Error from server: {data.get('message')}")
            
        else:
            print(f"❓ Unknown message type: {msg_type}")

    async def initialize_resource_tracking(self, data: dict):
        """🆕 初始化资源追踪"""
        try:
            game_state = data.get('game_state')
            if isinstance(game_state, str):
                import json
                game_state = json.loads(game_state)
            elif game_state is None:
                return
            
            players_data = game_state.get('players', {})
            
            # 初始化所有玩家的资源状态
            for color, player_data in players_data.items():
                resource_cards = player_data.get('resource_cards', {})
                dev_cards = player_data.get('development_cards', {})
                victory_points = player_data.get('victory_points', 0)
                
                self.previous_resources[color] = {
                    'resource_cards': resource_cards.copy(),
                    'development_cards': dev_cards.copy(),
                    'victory_points': victory_points
                }
            
            print(f"\n🎯 INITIAL GAME STATE - ALL PLAYERS RESOURCES:")
            await self.display_all_players_resources(players_data, "GAME START")
            
        except Exception as e:
            print(f"⚠️ Error initializing resource tracking: {e}")

    async def check_resource_changes(self, data):
        """🆕 检查并显示资源变动"""
        try:
            game_state_json = data.get('game_state')
            if not game_state_json:
                return
                
            # 提取所有玩家的资源
            players_data = game_state_json.get('players', {})
            
            current_resources = {}
            for color_str, player_data in players_data.items():
                if isinstance(player_data, dict):
                    resource_deck = player_data.get('resource_deck', {})
                    if isinstance(resource_deck, dict):
                        # 转换资源格式 {resource: count} -> [wood, brick, sheep, wheat, ore]
                        resources = [
                            resource_deck.get('WOOD', 0),
                            resource_deck.get('BRICK', 0), 
                            resource_deck.get('SHEEP', 0),
                            resource_deck.get('WHEAT', 0),
                            resource_deck.get('ORE', 0)
                        ]
                        current_resources[color_str] = resources
            
            # 显示当前资源状态
            await self.display_all_players_resources(current_resources)
            
            # 检查变动（如果有之前的记录）
            if hasattr(self, 'previous_resources') and self.previous_resources:
                await self.display_resource_changes(self.previous_resources, current_resources)
            
            # 更新记录
            self.previous_resources = current_resources.copy()
            
        except Exception as e:
            print(f"⚠️ Error checking resource changes: {e}")

    async def display_all_players_resources(self, current_resources):
        """🆕 显示所有玩家的当前资源"""
        print(f"\n{'='*60}")
        print(f"💰 ALL PLAYERS RESOURCES STATUS 💰")
        print(f"{'='*60}")
        
        resource_names = ['WOOD', 'BRICK', 'SHEEP', 'WHEAT', 'ORE']
        resource_emojis = ['🌲', '🧱', '🐑', '🌾', '⛰️']
        
        # 表头
        print(f"{'PLAYER':<8} | {'🌲':<3} {'🧱':<3} {'🐑':<3} {'🌾':<3} {'⛰️':<3} | TOTAL")
        print(f"{'-'*8} | {'-'*15} | {'-'*5}")
        
        for color_str, resources in current_resources.items():
            total = sum(resources)
            color_indicator = "🔥" if color_str == self.color.value else "  "
            
            # 格式化资源显示
            resource_display = " ".join(f"{count:>2}" for count in resources)
            
            print(f"{color_str:<8} | {resource_display} | {total:>3} {color_indicator}")
        
        print(f"{'='*60}")

    async def display_resource_changes(self, previous, current):
        """🆕 显示资源变动"""
        print(f"\n📈 RESOURCE CHANGES:")
        
        resource_names = ['WOOD', 'BRICK', 'SHEEP', 'WHEAT', 'ORE'] 
        resource_emojis = ['🌲', '🧱', '🐑', '🌾', '⛰️']
        
        changes_found = False
        
        for color_str in current.keys():
            if color_str in previous:
                prev_resources = previous[color_str]
                curr_resources = current[color_str]
                
                player_changes = []
                for i, (prev, curr) in enumerate(zip(prev_resources, curr_resources)):
                    diff = curr - prev
                    if diff != 0:
                        emoji = resource_emojis[i]
                        resource = resource_names[i]
                        if diff > 0:
                            player_changes.append(f"+{diff}{emoji}")
                        else:
                            player_changes.append(f"{diff}{emoji}")
                
                if player_changes:
                    changes_found = True
                    changes_str = " ".join(player_changes)
                    color_indicator = "🔥" if color_str == self.color.value else "  "
                    print(f"  {color_str:<8}: {changes_str} {color_indicator}")
        
        if not changes_found:
            print(f"  📊 No resource changes detected")

    async def display_trade_summary(self, action_data):
        """🆕 显示交易摘要"""
        action_type = action_data.get('action_type')
        if action_type not in ['OFFER_TRADE', 'ACCEPT_TRADE', 'CONFIRM_TRADE', 'REJECT_TRADE', 'CANCEL_TRADE']:
            return
            
        print(f"\n🤝 TRADE SUMMARY:")
        
        if action_type == 'OFFER_TRADE':
            value = action_data.get('value', [])
            if len(value) >= 10:
                give_resources = value[:5]
                want_resources = value[5:10]
                
                give_items = self.format_resources(give_resources)
                want_items = self.format_resources(want_resources)
                
                print(f"  📤 {self.color.value} offers: {give_items}")
                print(f"  📥 {self.color.value} wants: {want_items}")
        
        elif action_type == 'CONFIRM_TRADE':
            value = action_data.get('value', [])
            if len(value) >= 11:
                give_resources = value[:5]
                want_resources = value[5:10]
                partner_color = value[10]
                
                give_items = self.format_resources(give_resources)
                want_items = self.format_resources(want_resources)
                
                print(f"  ✅ {self.color.value} confirms trade with {partner_color}")
                print(f"  📤 {self.color.value} gives: {give_items}")
                print(f"  📥 {self.color.value} gets: {want_items}")

    def format_resources(self, resources):
        """🆕 格式化资源显示"""
        if not resources or len(resources) < 5:
            return "None"
            
        resource_names = ['WOOD', 'BRICK', 'SHEEP', 'WHEAT', 'ORE']
        resource_emojis = ['🌲', '🧱', '🐑', '🌾', '⛰️']
        
        items = []
        for i, count in enumerate(resources):
            if count > 0:
                emoji = resource_emojis[i]
                name = resource_names[i]
                items.append(f"{count}{emoji}")
        
        return " + ".join(items) if items else "None"

    async def handle_action_request(self, data: dict):
        """處理行動請求（修复版本）"""
        self.action_count += 1
        
        try:
            print(f"\n{'🎯'*20}")
            print(f"🎯 ACTION REQUEST #{self.action_count:03d} FOR {self.color.value:6s} 🎯")
            print(f"{'🎯'*20}")
            
            # 重建遊戲狀態
            game_state_json = data.get('game_state')
            playable_actions_data = data.get('playable_actions', [])
            
            # 🆕 显示所有玩家资源状态 - 每次行动请求时都显示
            await self.check_resource_changes(data)
            
            print(f"\n📋 Available actions: {len(playable_actions_data)}")
            
            # 檢查是否有可用行動
            if not playable_actions_data:
                print("⚠️ No available actions!")
                await self.send_message({
                    'type': 'action',
                    'action': None
                })
                return
            
            # 🔧 過濾交易行動（移除已達上限的交易）- 简化版本
            filtered_actions = []
            blocked_trades = 0
            
            for i, action_data in enumerate(playable_actions_data):
                action_type = action_data.get('action_type')
                
                if action_type == 'OFFER_TRADE':
                    # 🔧 简化：总是允许交易
                    filtered_actions.append((i, action_data))
                else:
                    filtered_actions.append((i, action_data))
            
            if blocked_trades > 0:
                print(f"🚫 Blocked {blocked_trades} trade proposals (reached limit)")
            
            # 🔧 美化行動列表顯示
            await self.display_actions_beautifully(filtered_actions)
            
            # 🔍 特別標記交易相關行動
            trade_actions = [
                (i, action_data) for i, action_data in filtered_actions
                if action_data.get('action_type') in ['ACCEPT_TRADE', 'REJECT_TRADE', 'CONFIRM_TRADE', 'CANCEL_TRADE', 'OFFER_TRADE']
            ]
            
            await self.display_trade_actions(trade_actions, data)
            
            # 從 JSON 重建遊戲對象
            game = self.reconstruct_game_from_json(game_state_json)
            
            # 使用 LLM 做決策（使用過濾後的行動）
            print(f"\n🧠 Making LLM decision...")
            chosen_action_index = await self.make_real_llm_decision(game, [action_data for _, action_data in filtered_actions])
            
            await self.send_chosen_action(chosen_action_index, filtered_actions, playable_actions_data)
                
        except Exception as e:
            print(f"❌ Error handling action request: {e}")
            import traceback
            traceback.print_exc()
            
            # 發送空行動作為最後後備
            try:
                await self.send_message({
                    'type': 'action',
                    'action': None
                })
            except:
                pass

    async def handle_game_state_update(self, data: dict):
        """🆕 处理游戏状态更新"""
        try:
            # 获取游戏状态
            game_state_json = data.get('game_state')
            if not game_state_json:
                return
            
            # 检查是否是我们关心的更新
            current_turn = data.get('current_turn')
            is_my_turn = current_turn == self.color.value if current_turn else False
            
            # 显示资源变化（每次状态更新都检查）
            await self.check_resource_changes(data)
            
            # 显示当前回合状态
            if is_my_turn:
                print(f"📊 Game state updated. 🔥 MY TURN")
            else:
                print(f"📊 Game state updated. ⏳ {current_turn}'s turn")
            
            # 特别处理某些行动的结果
            last_action = data.get('last_action')
            if last_action:
                await self.handle_action_result(last_action)
            
        except Exception as e:
            print(f"⚠️ Error handling game state update: {e}")

    async def handle_action_result(self, action_data):
        """🆕 处理行动结果"""
        try:
            action_type = action_data.get('action_type')
            action_color = action_data.get('color')
            
            # 显示交易相关的特殊信息
            if action_type in ['MARITIME_TRADE', 'CONFIRM_TRADE']:
                await self.display_trade_summary(action_data)
            
            # 显示特殊行动的效果
            if action_type == 'ROLL':
                print(f"🎲 {action_color} rolled the dice!")
            elif action_type == 'BUILD_ROAD':
                print(f"🛤️ {action_color} built a road")
            elif action_type == 'BUILD_SETTLEMENT':
                print(f"🏠 {action_color} built a settlement")
            elif action_type == 'BUILD_CITY':
                print(f"🏙️ {action_color} built a city")
            elif action_type == 'BUY_DEVELOPMENT_CARD':
                print(f"🃏 {action_color} bought a development card")
            elif action_type == 'MARITIME_TRADE':
                value = action_data.get('value', [])
                if len(value) >= 5:
                    give_resources = value[:2]  # 前两个是给出的资源
                    get_resource = value[4]     # 第5个是获得的资源
                    give_str = " + ".join(filter(None, give_resources))
                    print(f"🚢 {action_color} traded {give_str} → {get_resource}")
                    
        except Exception as e:
            print(f"⚠️ Error handling action result: {e}")
            
    async def send_chosen_action(self, chosen_action_index, filtered_actions, playable_actions_data):
        """🆕 发送选择的行动"""
        try:
            if 0 <= chosen_action_index < len(filtered_actions):
                original_index, chosen_action_data = filtered_actions[chosen_action_index]
                
                print(f"🎯 Chosen action #{chosen_action_index}: {chosen_action_data.get('action_type')}")
                print(f"📤 Sending action: {chosen_action_data.get('description', 'N/A')}")
                
                # 准备行动消息
                action_message = await self.prepare_action_message(chosen_action_data)
                
                await self.send_message({
                    'type': 'action',
                    'action': action_message
                })
            else:
                print(f"⚠️ Invalid action index: {chosen_action_index}")
                await self.send_message({
                    'type': 'action',
                    'action': None
                })
                
        except Exception as e:
            print(f"❌ Error sending action: {e}")
            await self.send_message({
                'type': 'action',
                'action': None
            })

    async def prepare_action_message(self, action_data):
        """🔧 修复：准备行动消息 - 确保正确的数据格式"""
        try:
            action_type = action_data.get('action_type')
            value = action_data.get('value')

            return [
                self.color.value,
                action_type,
                value  # 保持原始格式
            ]
        except Exception as e:
            print(f"⚠️ Error preparing action message: {e}")
            return None

    async def send_fallback_action(self, filtered_actions, playable_actions_data):
        """🆕 发送后备行动"""
        print(f"\n🔄 Using fallback action selection...")
        
        if filtered_actions:
            # 选择第一个可用行动
            original_index, fallback_action = filtered_actions[0]
            print(f"📤 Sending fallback action: {fallback_action.get('description')}")
            
            action_message = await self.prepare_action_message(fallback_action)
            await self.send_message({
                'type': 'action',
                'action': action_message
            })
        else:
            # 发送空行动
            await self.send_message({
                'type': 'action',
                'action': None
            })
            print("📤 Sent empty action (no alternatives available)")
            
    async def make_real_llm_decision(self, game, playable_actions_data):
        """🆕 使用真正的LLM做决策"""
        # 檢查速率限制
        current_time = time.time()
        if current_time - self.last_api_call < self.min_interval:
            wait_time = self.min_interval - (current_time - self.last_api_call)
            print(f"⏳ Rate limiting: waiting {wait_time:.1f} seconds...")
            await asyncio.sleep(wait_time)
        
        # 從 playable_actions_data 重建 Action 對象
        # 🔧 修复：正确的导入路径
        from catanatron.json import action_from_json
        playable_actions = []
        for action_data in playable_actions_data:
            try:
                action_json = [
                    self.color.value,
                    action_data['action_type'],
                    action_data['value']
                ]
                action = action_from_json(action_json)
                playable_actions.append(action)
            except Exception as e:
                print(f"⚠️ Failed to reconstruct action: {e}")
                continue
        
        if not playable_actions:
            print(f"❌ No valid actions reconstructed for {self.color.value}")
            return 0
        
        # 使用真正的 LLM 做決策
        print(f"🧠 Asking LLM for decision among {len(playable_actions)} actions...")
        chosen_action = self.llm_player.decide(game, playable_actions)
        
        if chosen_action is None:
            print(f"⚠️ LLM returned None, using first action as fallback")
            return 0
        
        # 找到選擇的行動在原始列表中的索引
        try:
            chosen_index = playable_actions.index(chosen_action)
            self.last_api_call = time.time()
            chosen_desc = playable_actions_data[chosen_index].get('description')
            print(f"✅ LLM chose action {chosen_index}: {chosen_desc}")
            return chosen_index
        except ValueError:
            print(f"⚠️ LLM returned action not in list, using first action as fallback")
            return 0
                
        except Exception as e:
            print(f"❌ Error in LLM decision: {e}")
            import traceback
            traceback.print_exc()
            return 0

    async def intelligent_fallback_decision(self, playable_actions_data):
        """🆕 智能后备决策"""
        # 智能後備：優先選擇有意義的行動
        action_priorities = {
            'CONFIRM_TRADE': 100,  # 🆕 最高优先级
            'CANCEL_TRADE': 95,
            'ACCEPT_TRADE': 90,
            'REJECT_TRADE': 85,
            'BUILD_SETTLEMENT': 70,
            'BUILD_CITY': 65,
            'BUILD_ROAD': 60,
            'BUY_DEVELOPMENT_CARD': 55,
            'ROLL': 50,
            'OFFER_TRADE': 30,
            'END_TURN': 10
        }
        
        best_score = -1
        best_index = 0
        
        for i, action_data in enumerate(playable_actions_data):
            action_type = action_data.get('action_type', '')
            score = action_priorities.get(action_type, 20)
            if score > best_score:
                best_score = score
                best_index = i
        
        chosen_action = playable_actions_data[best_index]
        print(f"🎯 Intelligent fallback chose: {chosen_action.get('action_type')} (score: {best_score})")
        return best_index

    async def make_real_llm_decision(self, game, playable_actions_data):
        """🆕 使用真正的LLM做决策"""
        # 檢查速率限制
        current_time = time.time()
        if current_time - self.last_api_call < self.min_interval:
            wait_time = self.min_interval - (current_time - self.last_api_call)
            print(f"⏳ Rate limiting: waiting {wait_time:.1f} seconds...")
            await asyncio.sleep(wait_time)
        
        # 從 playable_actions_data 重建 Action 對象
        from catanatron.json import action_from_json
        playable_actions = []
        for action_data in playable_actions_data:
            try:
                action_json = [
                    self.color.value,
                    action_data['action_type'],
                    action_data['value']
                ]
                action = action_from_json(action_json)
                playable_actions.append(action)
            except Exception as e:
                print(f"⚠️ Failed to reconstruct action: {e}")
                continue
        
        if not playable_actions:
            print(f"❌ No valid actions reconstructed for {self.color.value}")
            return 0
        
        # 使用真正的 LLM 做決策
        print(f"🧠 Asking LLM for decision among {len(playable_actions)} actions...")
        chosen_action = self.llm_player.decide(game, playable_actions)
        
        if chosen_action is None:
            print(f"⚠️ LLM returned None, using first action as fallback")
            return 0
        
        # 找到選擇的行動在原始列表中的索引
        try:
            chosen_index = playable_actions.index(chosen_action)
            self.last_api_call = time.time()
            chosen_desc = playable_actions_data[chosen_index].get('description')
            print(f"✅ LLM chose action {chosen_index}: {chosen_desc}")
            return chosen_index
        except ValueError:
            print(f"⚠️ LLM returned action not in list, using first action as fallback")
            return 0
                
        except Exception as e:
            print(f"❌ Error in LLM decision: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def reconstruct_game_from_json(self, game_state_json: str):
        """從 JSON 重建遊戲對象"""
        try:
            # 簡化處理，LLM 玩家可以處理 None 遊戲對象
            return None
        except Exception as e:
            print(f"⚠️ Error reconstructing game from JSON: {e}")
            return None

    async def send_message(self, message: dict):
        """發送訊息給服務器"""
        if self.websocket and self.connected:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                print(f"❌ Error sending message: {e}")
                self.connected = False

    async def disconnect(self):
        """斷開連接"""
        if self.websocket:
            await self.websocket.close()
        self.connected = False
    async def send_fallback_action(self, filtered_actions, playable_actions_data):
        """🆕 发送后备行动"""
        print(f"\n🔄 Using fallback action selection...")
        
        if filtered_actions:
            # 选择第一个可用行动
            original_index, fallback_action = filtered_actions[0]
            print(f"📤 Sending fallback action: {fallback_action.get('description')}")
            
            action_message = await self.prepare_action_message(fallback_action)
            await self.send_message({
                'type': 'action',
                'action': action_message
            })
        else:
            # 发送空行动
            await self.send_message({
                'type': 'action',
                'action': None
            })
            print("📤 Sent empty action (no alternatives available)")
            
    def record_trade_proposal(self, trade_value):
        """🚫 删除：不再记录交易提议"""
        pass  # 简化为空函数
        
    async def display_resource_changes(self, previous, current):
        """🆕 显示资源变动（增强版）"""
        print(f"\n📈 RESOURCE CHANGES ANALYSIS:")
        print(f"{'='*60}")
        
        resource_names = ['WOOD', 'BRICK', 'SHEEP', 'WHEAT', 'ORE'] 
        resource_emojis = ['🌲', '🧱', '🐑', '🌾', '⛰️']
        
        changes_found = False
        total_changes = 0
        
        for color_str in current.keys():
            if color_str in previous:
                prev_resources = previous[color_str]
                curr_resources = current[color_str]
                
                player_changes = []
                player_total_change = 0
                
                for i, (prev, curr) in enumerate(zip(prev_resources, curr_resources)):
                    diff = curr - prev
                    if diff != 0:
                        emoji = resource_emojis[i]
                        resource = resource_names[i]
                        if diff > 0:
                            player_changes.append(f"+{diff}{emoji}")
                            player_total_change += diff
                        else:
                            player_changes.append(f"{diff}{emoji}")
                            player_total_change += abs(diff)
                
                if player_changes:
                    changes_found = True
                    total_changes += player_total_change
                    changes_str = " ".join(player_changes)
                    color_indicator = "🔥" if color_str == self.color.value else "  "
                    
                    # 显示变动类型
                    net_change = sum(curr_resources) - sum(prev_resources)
                    if net_change > 0:
                        trend = "📈 GAINED"
                    elif net_change < 0:
                        trend = "📉 LOST"
                    else:
                        trend = "🔄 TRADED"
                    
                    print(f"  {color_str:<8}: {changes_str} {trend} {color_indicator}")
        
        if not changes_found:
            print(f"  📊 No resource changes detected")
        else:
            print(f"\n💫 Total Economic Activity: {total_changes} resource movements")
        
        print(f"{'='*60}")
        
    def can_propose_trade(self, value):
        """🔧 简化：总是允许交易提议"""
        return True  # 不再限制交易次数
    
    async def display_actions_beautifully(self, filtered_actions):
        """🆕 美化行动列表显示"""
        if not filtered_actions:
            print("📋 No actions available")
            return
            
        print(f"\n📋 AVAILABLE ACTIONS ({len(filtered_actions)}):")
        print(f"{'='*80}")
        
        # 按类型分组行动
        action_groups = {}
        for i, (original_idx, action_data) in enumerate(filtered_actions):
            action_type = action_data.get('action_type', 'UNKNOWN')
            if action_type not in action_groups:
                action_groups[action_type] = []
            action_groups[action_type].append((i, original_idx, action_data))
        
        # 定义行动类型的显示顺序和图标
        action_display_order = {
            'ROLL': '🎲',
            'BUILD_SETTLEMENT': '🏠', 
            'BUILD_CITY': '🏙️',
            'BUILD_ROAD': '🛤️',
            'BUY_DEVELOPMENT_CARD': '🃏',
            'PLAY_KNIGHT_CARD': '⚔️',
            'PLAY_YEAR_OF_PLENTY': '💰',
            'PLAY_MONOPOLY': '💎',
            'PLAY_ROAD_BUILDING': '🛤️',
            'MARITIME_TRADE': '🚢',
            'OFFER_TRADE': '🤝',
            'ACCEPT_TRADE': '✅',
            'REJECT_TRADE': '❌',
            'CONFIRM_TRADE': '🔒',
            'CANCEL_TRADE': '🔄',
            'MOVE_ROBBER': '🦹',
            'END_TURN': '🏁'
        }
        
        # 按顺序显示各类行动
        for action_type in action_display_order:
            if action_type in action_groups:
                emoji = action_display_order[action_type]
                actions_of_type = action_groups[action_type]
                
                print(f"\n{emoji} {action_type} ({len(actions_of_type)} available):")
                for i, original_idx, action_data in actions_of_type:
                    description = action_data.get('description', 'No description')
                    value_str = str(action_data.get('value', ''))
                    
                    # 美化交易行动的显示
                    if action_type in ['OFFER_TRADE', 'ACCEPT_TRADE', 'REJECT_TRADE', 'CONFIRM_TRADE']:
                        value_str = self.format_trade_action_display(action_data)
                    elif len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    
                    print(f"  [{i:2d}] {description}")
                    if value_str and value_str != 'None':
                        print(f"       💡 {value_str}")
        
        # 显示其他未分类的行动
        for action_type, actions_of_type in action_groups.items():
            if action_type not in action_display_order:
                print(f"\n❓ {action_type} ({len(actions_of_type)} available):")
                for i, original_idx, action_data in actions_of_type:
                    description = action_data.get('description', 'No description')
                    print(f"  [{i:2d}] {description}")
        
        print(f"{'='*80}")

    def format_trade_action_display(self, action_data):
        """🆕 格式化交易行动显示（增强版）"""
        value = action_data.get('value', [])
        action_type = action_data.get('action_type')
        
        # 处理海上贸易
        if action_type == 'MARITIME_TRADE':
            return self.format_maritime_trade_display(action_data)
        
        # 处理玩家间交易
        if action_type == 'OFFER_TRADE' and len(value) >= 10:
            give_resources = value[:5]
            want_resources = value[5:10]
            give_str = self.format_resources(give_resources)
            want_str = self.format_resources(want_resources)
            return f"Give: {give_str} → Want: {want_str}"
        
        elif action_type in ['ACCEPT_TRADE', 'REJECT_TRADE'] and len(value) >= 10:
            give_resources = value[:5]
            want_resources = value[5:10]
            give_str = self.format_resources(give_resources)
            want_str = self.format_resources(want_resources)
            return f"Trade: {give_str} ↔ {want_str}"
        
        elif action_type == 'CONFIRM_TRADE' and len(value) >= 11:
            give_resources = value[:5]
            want_resources = value[5:10]
            partner = value[10]
            give_str = self.format_resources(give_resources)
            want_str = self.format_resources(want_resources)
            return f"Confirm with {partner}: Give {give_str} → Get {want_str}"
        
        return str(value)

    async def format_maritime_trade_display(self, action_data):
        """🆕 格式化海上贸易显示"""
        value = action_data.get('value', [])
        if len(value) >= 5:
            give_items = []
            get_item = None
            
            # 处理给出的资源（前面的非None项）
            for item in value[:4]:
                if item is not None:
                    give_items.append(item)
            
            # 处理获得的资源（最后一个）
            if len(value) > 4 and value[4] is not None:
                get_item = value[4]
            
            if give_items and get_item:
                give_str = " + ".join(give_items)
                resource_emoji_map = {
                    'WOOD': '🌲', 'BRICK': '🧱', 'SHEEP': '🐑', 
                    'WHEAT': '🌾', 'ORE': '⛰️'
                }
                
                give_emoji = "".join(resource_emoji_map.get(r, r) for r in give_items)
                get_emoji = resource_emoji_map.get(get_item, get_item)
                
                return f"Trade: {give_str} {give_emoji} → {get_item} {get_emoji}"
        
        return str(value)

    async def display_trade_actions(self, trade_actions, data):
        """🆕 显示交易相关行动（简化版）"""
        if not trade_actions:
            return
            
        print(f"\n🤝 TRADE ACTIONS:")
        trade_counts = {}
        for i, action_data in trade_actions:
            action_type = action_data.get('action_type')
            trade_counts[action_type] = trade_counts.get(action_type, 0) + 1
        
        if trade_counts:
            for action_type, count in trade_counts.items():
                emoji_map = {
                    'OFFER_TRADE': '📤',
                    'ACCEPT_TRADE': '✅',
                    'REJECT_TRADE': '❌',
                    'CONFIRM_TRADE': '🔒',
                    'CANCEL_TRADE': '🔄'
                }
                emoji = emoji_map.get(action_type, '🤝')
                print(f"  {emoji} {action_type}: {count} available")
                    
    async def check_resource_changes(self, data):
        """🆕 检查并显示资源变动（简化版）"""
        try:
            game_state_json = data.get('game_state')
            if not game_state_json:
                return
                
            # 简化处理 - 只在初始化时显示一次
            if not hasattr(self, '_resource_initialized'):
                print(f"📊 Game state received for {self.color.value}")
                self._resource_initialized = True
                
        except Exception as e:
            print(f"⚠️ Error checking resources: {e}")

    async def display_actions_beautifully(self, filtered_actions):
        """🆕 美化行动列表显示（简化版）"""
        if not filtered_actions:
            return
            
        print(f"\n📋 AVAILABLE ACTIONS ({len(filtered_actions)}):")
        print("=" * 60)
        
        # 按类型分组显示
        action_groups = {}
        for i, (original_index, action_data) in enumerate(filtered_actions):
            action_type = action_data.get('action_type', 'UNKNOWN')
            if action_type not in action_groups:
                action_groups[action_type] = []
            action_groups[action_type].append((i, original_index, action_data))
        
        for action_type, actions in action_groups.items():
            emoji_map = {
                'BUILD_SETTLEMENT': '🏠',
                'BUILD_ROAD': '🛤️',
                'BUILD_CITY': '🏙️',
                'BUY_DEVELOPMENT_CARD': '🎴',
                'OFFER_TRADE': '📤',
                'ACCEPT_TRADE': '✅',
                'REJECT_TRADE': '❌',
                'CONFIRM_TRADE': '🔒',
                'CANCEL_TRADE': '🔄',
                'MARITIME_TRADE': '🚢',
                'END_TURN': '🏁'
            }
            emoji = emoji_map.get(action_type, '🎯')
            
            print(f"{emoji} {action_type} ({len(actions)} available):")
            for i, original_index, action_data in actions[:3]:  # 只显示前3个
                description = action_data.get('description', '')
                print(f"  [{i:2d}] {description}")
            
            if len(actions) > 3:
                print(f"  ... and {len(actions) - 3} more")
            print()
        
        print("=" * 60)

# 命令行啟動
async def main():
    parser = argparse.ArgumentParser(description='LLM Agent Client for Catan')
    parser.add_argument('--host', default='localhost', help='Game server host')
    parser.add_argument('--port', type=int, required=True, help='Game server port')
    parser.add_argument('--color', required=True, choices=['RED', 'BLUE', 'WHITE', 'ORANGE'], 
                       help='Player color')
    parser.add_argument('--model', default='gemini-1.5-flash', 
                       help='LLM model name')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug mode with auto-decisions for testing')
    parser.add_argument('--max-trades', type=int, default=3,
                       help='Maximum trade proposals per resource type (default: 3)')
    
    args = parser.parse_args()
    
    color = Color[args.color]
    client = LLMAgentClient(args.host, args.port, color, args.model)
    
    # 設置調試模式和交易限制
    if args.debug:
        client.debug_mode = True
        print(f"🔧 Debug mode enabled for {color.value}")
    
    client.max_trades_per_player = args.max_trades
    print(f"📊 Max trade proposals per resource type: {args.max_trades}")
    
    try:
        await client.connect()
    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down {color.value} client...")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
