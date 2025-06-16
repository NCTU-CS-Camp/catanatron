import asyncio
import websockets
import json
import argparse
from typing import Optional, Dict, Tuple
import time
from collections import defaultdict, deque
import random

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
        self.min_interval = 5  # 增加到5秒間隔以避免API限制
        
        # 修复：添加缺失的属性初始化
        self.action_count = 0  # 行动计数器
        self.current_turn = 0  # 回合追蹤
        self.previous_resources = {}  # 资源追踪
        self.debug_mode = False  # 调试模式
        
        # 简化：删除详细的交易追蹤
        self.trade_proposals_count = {}
        self.max_trade_proposals = 3
        
        # 建立 LLM 玩家實例
        try:
            from catanatron.players.llm import LLMPlayer
            self.llm_player = LLMPlayer(color, model_name)
            print(f"Created LLM player for {color.value} using {model_name}")
        except Exception as e:
            print(f"Failed to create LLM player: {e}")
            self.llm_player = None

    async def connect(self):
        """連接到遊戲服務器"""
        try:
            uri = f"ws://{self.server_host}:{self.server_port}"
            self.websocket = await websockets.connect(uri)
            self.connected = True
            print(f"\033[92mConnected as {self.color.value} player\033[0m")
            
            # 啟動消息循環
            await self.message_loop()
        except Exception as e:
            print(f"\033[91mConnection error: {e}\033[0m")
            self.connected = False

    async def message_loop(self):
        """處理來自服務器的消息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print(f"\033[93mConnection closed for {self.color.value}\033[0m")
            self.connected = False
        except Exception as e:
            print(f"\033[91mError in message loop: {e}\033[0m")
            self.connected = False

    async def handle_message(self, data: dict):
        """處理收到的訊息"""
        msg_type = data.get('type')
        
        if msg_type == 'welcome':
            print(f"Received welcome: {data.get('message')}")
            
        elif msg_type == 'game_started':
            print(f"Game started!")
            # 初始化资源追踪
            await self.initialize_resource_tracking(data)
            
        elif msg_type == 'game_state_update':
            current_player = data.get('current_player')
            is_my_turn = current_player == self.color.value
            turn_indicator = "\033[92mMY TURN\033[0m" if is_my_turn else f"\033[94m{current_player}'s turn\033[0m"
            print(f"\033[96mGame state updated. {turn_indicator}\033[0m")
            
            # 🆕 检查资源变动
            await self.check_resource_changes(data)
            
            # 檢測新回合並重置交易計數
            debug_info = data.get('debug_info', {})
            turn_number = debug_info.get('turn_number', 0)
            if turn_number > self.current_turn:
                self.current_turn = turn_number
                # 簡化：不再追蹤交易計數
            
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
            print(f"\033[91mError from server: {data.get('message')}\033[0m")
            
        else:
            print(f"❓ Unknown message type: {msg_type}")

    async def initialize_resource_tracking(self, data: dict):
        """初始化资源追踪"""
        try:
            game_state_json = data.get('game_state')
            if not game_state_json:
                return
                
            # 解析游戏状态
            if isinstance(game_state_json, str):
                game_state = json.loads(game_state_json)
            else:
                game_state = game_state_json
            
            # 获取玩家状态
            player_state = game_state.get('player_state', {})
            
            # 初始化资源追踪
            self.previous_resources = {}
            for color_str, state_info in player_state.items():
                if isinstance(state_info, dict) and 'freqdeck' in state_info:
                    freqdeck = state_info['freqdeck']
                    if isinstance(freqdeck, list) and len(freqdeck) >= 5:
                        self.previous_resources[color_str] = freqdeck[:5].copy()
            
            # 显示初始状态
            if self.previous_resources:
                print(f"\n\033[96mINITIAL GAME STATE - ALL PLAYERS RESOURCES:\033[0m")
                await self.display_all_player_resources(self.previous_resources)
                
        except Exception as e:
            print(f"\033[93mError initializing resource tracking: {e}\033[0m")

    async def check_resource_changes(self, data):
        """检查并显示资源变动"""
        try:
            game_state_json = data.get('game_state')
            if not game_state_json:
                return
                
            # 解析游戏状态
            if isinstance(game_state_json, str):
                game_state = json.loads(game_state_json)
            else:
                game_state = game_state_json
            
            # 获取当前玩家状态
            player_state = game_state.get('player_state', {})
            current_resources = {}
            
            for color_str, state_info in player_state.items():
                if isinstance(state_info, dict) and 'freqdeck' in state_info:
                    freqdeck = state_info['freqdeck']
                    if isinstance(freqdeck, list) and len(freqdeck) >= 5:
                        current_resources[color_str] = freqdeck[:5].copy()
            
            # 检查变动
            if hasattr(self, 'previous_resources') and self.previous_resources:
                # 检查是否有变动
                has_changes = False
                for color_str in current_resources:
                    if color_str in self.previous_resources:
                        if current_resources[color_str] != self.previous_resources[color_str]:
                            has_changes = True
                            break
                
                if has_changes:
                    await self.display_resource_changes(self.previous_resources, current_resources)
                
                # 更新追踪
                self.previous_resources = current_resources.copy()
            else:
                # 首次初始化
                self.previous_resources = current_resources.copy()
                
        except Exception as e:
            print(f"\033[93mError checking resource changes: {e}\033[0m")

    async def display_all_player_resources(self, resources):
        """显示所有玩家的当前资源"""
        try:
            print(f"\033[95mALL PLAYERS RESOURCES STATUS\033[0m")
            print("=" * 60)
            
            resource_names = ['WOOD', 'BRICK', 'SHEEP', 'WHEAT', 'ORE']
            
            print(f"{'PLAYER':<8} | {'WOOD':<4} {'BRICK':<5} {'SHEEP':<5} {'WHEAT':<5} {'ORE':<3} | TOTAL")
            print("-" * 60)
            
            for color_str, freqdeck in resources.items():
                if len(freqdeck) >= 5:
                    color_indicator = "\033[92m*\033[0m" if color_str == self.color.value else " "
                    total = sum(freqdeck[:5])
                    print(f"{color_indicator}{color_str:<7} | {freqdeck[0]:<4} {freqdeck[1]:<5} {freqdeck[2]:<5} {freqdeck[3]:<5} {freqdeck[4]:<3} | {total}")
            
            print("=" * 60)
        except Exception as e:
            print(f"\033[93mError displaying resources: {e}\033[0m")

    async def display_resource_changes(self, previous, current):
        """显示资源变动"""
        print(f"\n\033[95mRESOURCE CHANGES:\033[0m")
        print("=" * 40)
        
        resource_names = ['WOOD', 'BRICK', 'SHEEP', 'WHEAT', 'ORE']
        
        changes_found = False
        
        for color_str in current.keys():
            if color_str in previous:
                prev_resources = previous[color_str]
                curr_resources = current[color_str]
                
                player_changes = []
                
                for i, (prev, curr) in enumerate(zip(prev_resources, curr_resources)):
                    diff = curr - prev
                    if diff != 0:
                        resource = resource_names[i]
                        if diff > 0:
                            player_changes.append(f"+{diff}{resource}")
                        else:
                            player_changes.append(f"{diff}{resource}")
                
                if player_changes:
                    changes_found = True
                    color_indicator = "\033[92m*\033[0m" if color_str == self.color.value else " "
                    change_str = " ".join(player_changes)
                    print(f"{color_indicator}{color_str}: {change_str}")
        
        if not changes_found:
            print(f"  \033[94mNo resource changes detected\033[0m")

    async def display_trade_summary(self, action_data):
        """显示交易摘要"""
        action_type = action_data.get('action_type')
        if action_type not in ['OFFER_TRADE', 'ACCEPT_TRADE', 'CONFIRM_TRADE', 'REJECT_TRADE', 'CANCEL_TRADE']:
            return
            
        print(f"\n\033[95mTRADE SUMMARY:\033[0m")
        
        if action_type == 'OFFER_TRADE':
            value = action_data.get('value', [])
            if len(value) >= 10:
                give_resources = value[:5]
                want_resources = value[5:10]
                
                give_items = self.format_resources(give_resources)
                want_items = self.format_resources(want_resources)
                
                print(f"  \033[93mOFFER\033[0m {self.color.value} offers: {give_items}")
                print(f"  \033[92mWANT\033[0m {self.color.value} wants: {want_items}")
        
        elif action_type == 'CONFIRM_TRADE':
            value = action_data.get('value', [])
            if len(value) >= 11:
                give_resources = value[:5]
                want_resources = value[5:10]
                partner_color = value[10]
                
                give_items = self.format_resources(give_resources)
                want_items = self.format_resources(want_resources)
                
                print(f"  \033[92mCONFIRM\033[0m {self.color.value} confirms trade with {partner_color}")
                print(f"  \033[93mGIVE\033[0m {self.color.value} gives: {give_items}")
                print(f"  \033[92mGET\033[0m {self.color.value} gets: {want_items}")

    def format_resources(self, resources):
        """格式化資源顯示"""
        if not resources or len(resources) < 5:
            return "No resources"
        
        resource_names = ['WOOD', 'BRICK', 'SHEEP', 'WHEAT', 'ORE']
        resource_parts = []
        
        for i, count in enumerate(resources[:5]):
            if count > 0:
                resource_parts.append(f"{count}{resource_names[i]}")
        
        return " + ".join(resource_parts) if resource_parts else "No resources"

    async def handle_action_request(self, data):
        """Handle action request from server"""
        try:
            playable_actions_data = data.get('playable_actions', [])
            game_state_json = data.get('game_state')
            
            if not playable_actions_data:
                print(f"\033[93mNo actions available for {self.color.value}\033[0m")
                return
            
            # Filter actions
            filtered_actions = [(i, action_data) for i, action_data in enumerate(playable_actions_data)]
            
            print(f"\n\033[96m{'='*60}\033[0m")
            print(f"\033[96mACTION REQUEST #{self.action_count:03d} FOR {self.color.value}\033[0m")
            print(f"\033[96m{'='*60}\033[0m")
            print(f"\nAvailable actions: \033[92m{len(filtered_actions)}\033[0m")
            
            # Display actions
            await self.display_actions_beautifully(filtered_actions)
            
            # Display trade actions summary
            await self.display_trade_actions(filtered_actions, data)
            
            # Make decision
            try:
                print("\n\033[94mMaking LLM decision...\033[0m")
                chosen_index = await self.make_llm_decision(filtered_actions, data)
                # chosen_index = self.llm_player.decide(game, playable_actions)
                
                if chosen_index is not None and 0 <= chosen_index < len(filtered_actions):
                    original_index, chosen_action = filtered_actions[chosen_index]
                    action_type = chosen_action.get('action_type')
                    print(f"\033[92mChosen action #{chosen_index}: {action_type}\033[0m")
                    
                    # 🆕 Send just the original action index as string instead of full action details
                    print(f"\033[95mSending action index: {original_index}\033[0m")
                    await self.send_message({
                        'type': 'action',
                        'action': str(original_index)  # Send only the action index as string
                    })
                else:
                    print("\033[93mInvalid action index, using fallback\033[0m")
                    await self.send_fallback_action(filtered_actions, playable_actions_data)
                    
            except Exception as e:
                print(f"\033[91mError in decision making: {e}\033[0m")
                await self.send_fallback_action(filtered_actions, playable_actions_data)
            
            self.action_count += 1
            
        except Exception as e:
            print(f"\033[91mError handling action request: {e}\033[0m")
            import traceback
            traceback.print_exc()

    async def make_llm_decision(self, filtered_actions, data):
        """Make decision using LLM"""
        if not filtered_actions:
            return None
            
        try:
            # Check rate limiting
            current_time = time.time()
            if current_time - self.last_api_call < self.min_interval:
                wait_time = self.min_interval - (current_time - self.last_api_call)
                print(f"Rate limiting: waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
            
            # Reconstruct game from JSON
            game_state_json = data.get('game_state')
            if not game_state_json:
                print("No game state available, using random choice")
                return random.randint(0, len(filtered_actions) - 1)
            
            game = self.reconstruct_game_from_json(game_state_json)
            if not game:
                print("Failed to reconstruct game, using random choice")
                return random.randint(0, len(filtered_actions) - 1)
            
            # Reconstruct actions
            playable_actions = []
            for _, action_data in filtered_actions:
                try:
                    action_json = [
                        self.color.value,
                        action_data['action_type'],
                        action_data['value']
                    ]
                    action = action_from_json(action_json)
                    playable_actions.append(action)
                except Exception as e:
                    print(f"Failed to reconstruct action: {e}")
                    continue
            
            if not playable_actions:
                print("No valid actions reconstructed")
                return 0
            
            # Use LLM to make decision
            print(f"Asking LLM for decision among {len(playable_actions)} actions...")
            chosen_action = self.llm_player.decide(game, playable_actions)
            
            if chosen_action is None:
                print("LLM returned None, using first action")
                return 0
            
            # Find chosen action index
            try:
                chosen_index = playable_actions.index(chosen_action)
                self.last_api_call = time.time()
                chosen_desc = filtered_actions[chosen_index][1].get('description')
                print(f"LLM chose action {chosen_index}: {chosen_desc}")
                return chosen_index
            except ValueError:
                print("LLM returned action not in list, using first action")
                return 0
                
        except Exception as e:
            print(f"Error in LLM decision: {e}")
            import traceback
            traceback.print_exc()
            return 0

    async def handle_game_state_update(self, data: dict):
        """處理游戲狀態更新"""
        try:
            # 獲取游戲狀態
            game_state_json = data.get('game_state')
            if not game_state_json:
                return
            
            # 初始化资源追踪
            if not hasattr(self, 'previous_resources'):
                await self.initialize_resource_tracking(data)
            
            # 檢查是否是我們關心的更新
            current_turn = data.get('current_turn')
            is_my_turn = current_turn == self.color.value if current_turn else False
            
            turn_indicator = "\033[92mMY TURN\033[0m" if is_my_turn else f"\033[94m{current_player}'s turn\033[0m"
            print(f"\033[96mGame state updated. {turn_indicator}\033[0m")
            
            # 检查资源变动
            await self.check_resource_changes(data)
            
            # 檢測新回合並重置交易計數
            debug_info = data.get('debug_info', {})
            turn_number = debug_info.get('turn_number', 0)
            if turn_number > self.current_turn:
                self.current_turn = turn_number
                # 簡化：不再追蹤交易計數
            
            # 特別處理某些行動的結果
            last_action = data.get('last_action')
            if last_action:
                await self.handle_action_result(last_action)
                
        except Exception as e:
            print(f"\033[93mError handling game state update: {e}\033[0m")

    async def handle_action_result(self, action_data):
        """处理行动结果"""
        try:
            action_type = action_data.get('action_type')
            action_color = action_data.get('color')
            
            # 显示交易相关的特殊信息
            if action_type in ['MARITIME_TRADE', 'CONFIRM_TRADE']:
                await self.display_trade_summary(action_data)
            
            # 显示特殊行动的效果
            if action_type == 'ROLL':
                print(f"\033[93mDICE\033[0m {action_color} rolled the dice!")
            elif action_type == 'BUILD_ROAD':
                print(f"\033[94mROAD\033[0m {action_color} built a road")
            elif action_type == 'BUILD_SETTLEMENT':
                print(f"\033[92mSETTLEMENT\033[0m {action_color} built a settlement")
            elif action_type == 'BUILD_CITY':
                print(f"\033[95mCITY\033[0m {action_color} built a city")
            elif action_type == 'BUY_DEVELOPMENT_CARD':
                print(f"\033[96mCARD\033[0m {action_color} bought a development card")
            elif action_type == 'MARITIME_TRADE':
                value = action_data.get('value', [])
                if len(value) >= 5:
                    give_resources = value[:2]  # 前两个是给出的资源
                    get_resource = value[4]     # 第5个是获得的资源
                    give_str = " + ".join(filter(None, give_resources))
                    print(f"\033[94mTRADE\033[0m {action_color} traded {give_str} -> {get_resource}")
                    
        except Exception as e:
            print(f"\033[93mError handling action result: {e}\033[0m")
            
    async def display_actions_beautifully(self, filtered_actions):
        """Display available actions in a clean format"""
        if not filtered_actions:
            print("No actions available")
            return
        
        # Group actions by type
        action_groups = {}
        for i, (original_idx, action_data) in enumerate(filtered_actions):
            action_type = action_data.get('action_type')
            if action_type not in action_groups:
                action_groups[action_type] = []
            action_groups[action_type].append((i, original_idx, action_data))
        
        # Display order and symbols
        action_display_order = {
            'ROLL': 'DICE',
            'BUILD_ROAD': 'ROAD',
            'BUILD_SETTLEMENT': 'SETTLEMENT', 
            'BUILD_CITY': 'CITY',
            'BUY_DEVELOPMENT_CARD': 'DEV_CARD',
            'MARITIME_TRADE': 'TRADE_BANK',
            'OFFER_TRADE': 'OFFER',
            'ACCEPT_TRADE': 'ACCEPT',
            'REJECT_TRADE': 'REJECT',
            'CONFIRM_TRADE': 'CONFIRM',
            'CANCEL_TRADE': 'CANCEL',
            'END_TURN': 'END_TURN'
        }
        
        print(f"\nAVAILABLE ACTIONS ({len(filtered_actions)}):")
        print("=" * 60)
        
        # Display actions by category
        for action_type in action_display_order:
            if action_type in action_groups:
                label = action_display_order[action_type]
                actions_of_type = action_groups[action_type]
                
                print(f"\n{label} ({len(actions_of_type)} available):")
                for i, original_idx, action_data in actions_of_type:
                    description = action_data.get('description', 'No description')
                    value_str = str(action_data.get('value', ''))
                    
                    # Format trade actions nicely
                    if action_type in ['OFFER_TRADE', 'ACCEPT_TRADE', 'REJECT_TRADE', 'CONFIRM_TRADE']:
                        value_str = self.format_trade_action_display(action_data)
                    elif len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    
                    print(f"  [{i:2d}] {description}")
                    if value_str and value_str != 'None':
                        print(f"       Details: {value_str}")
        
        # Display other uncategorized actions
        for action_type, actions_of_type in action_groups.items():
            if action_type not in action_display_order:
                print(f"\n{action_type} ({len(actions_of_type)} available):")
                for i, original_idx, action_data in actions_of_type:
                    description = action_data.get('description', 'No description')
                    print(f"  [{i:2d}] {description}")
        
        print("=" * 60)

    def format_trade_action_display(self, action_data):
        """格式化交易行動顯示"""
        value = action_data.get('value', [])
        action_type = action_data.get('action_type')
        
        # 處理海上貿易
        if action_type == 'MARITIME_TRADE':
            return self.format_maritime_trade_display(action_data)
        
        # 處理玩家間交易
        if action_type == 'OFFER_TRADE' and len(value) >= 10:
            give_resources = value[:5]
            want_resources = value[5:10]
            give_str = self.format_resources(give_resources)
            want_str = self.format_resources(want_resources)
            return f"Give: {give_str} -> Want: {want_str}"
        
        elif action_type in ['ACCEPT_TRADE', 'REJECT_TRADE'] and len(value) >= 10:
            give_resources = value[:5]
            want_resources = value[5:10]
            give_str = self.format_resources(give_resources)
            want_str = self.format_resources(want_resources)
            return f"Trade: {give_str} <-> {want_str}"
        
        elif action_type == 'CONFIRM_TRADE' and len(value) >= 11:
            give_resources = value[:5]
            want_resources = value[5:10]
            partner = value[10]
            give_str = self.format_resources(give_resources)
            want_str = self.format_resources(want_resources)
            partner_str = partner.value if hasattr(partner, 'value') else str(partner)
            return f"Confirm with {partner_str}: Give {give_str} -> Get {want_str}"
        
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
        """Display trade-related actions in a clean format"""
        if not trade_actions:
            return
            
        print(f"\nTRADE ACTIONS:")
        trade_counts = {}
        for i, action_data in trade_actions:
            action_type = action_data.get('action_type')
            trade_counts[action_type] = trade_counts.get(action_type, 0) + 1
        
        if trade_counts:
            for action_type, count in trade_counts.items():
                label_map = {
                    'OFFER_TRADE': 'OFFER',
                    'ACCEPT_TRADE': 'ACCEPT',
                    'REJECT_TRADE': 'REJECT',
                    'CONFIRM_TRADE': 'CONFIRM',
                    'CANCEL_TRADE': 'CANCEL'
                }
                label = label_map.get(action_type, action_type)
                print(f"  {label}: {count} available")

    async def prepare_action_message(self, action_data):
        """Prepare action message with proper data format"""
        try:
            action_type = action_data.get('action_type')
            value = action_data.get('value')
            
            # Handle Color objects in value
            if value is not None:
                if isinstance(value, (list, tuple)):
                    # Special handling for CONFIRM_TRADE - keep the last Color object as is
                    if action_type == 'CONFIRM_TRADE' and len(value) >= 11:
                        # Convert first 10 elements normally, keep last Color object
                        processed_value = []
                        for i, item in enumerate(value):
                            if i == 10:  # Last element should remain as Color object
                                # Import Color here to avoid circular imports
                                from catanatron.models.enums import Color
                                if isinstance(item, str):
                                    # Convert string back to Color object
                                    processed_value.append(Color[item])
                                else:
                                    processed_value.append(item)
                            else:
                                # Convert other Color objects to strings
                                if hasattr(item, 'value') and hasattr(item, 'name'):  # Color enum
                                    processed_value.append(item.value)
                                elif hasattr(item, 'name'):  # Other enums
                                    processed_value.append(item.name)
                                else:
                                    processed_value.append(item)
                        value = processed_value
                    else:
                        # Convert all Color objects to strings for other actions
                        processed_value = []
                        for item in value:
                            if hasattr(item, 'value') and hasattr(item, 'name'):  # Color enum
                                processed_value.append(item.value)
                            elif hasattr(item, 'name'):  # Other enums
                                processed_value.append(item.name)
                            else:
                                processed_value.append(item)
                        value = processed_value
                elif hasattr(value, 'value') and hasattr(value, 'name'):  # Single Color object
                    value = value.value
                elif hasattr(value, 'name'):  # Other enums
                    value = value.name

            return [
                self.color.value,
                action_type,
                value  # Use processed value
            ]
        except Exception as e:
            print(f"\033[91mError preparing action message: {e}\033[0m")
            import traceback
            traceback.print_exc()
            return None

    async def send_fallback_action(self, filtered_actions, playable_actions_data):
        """发送后备行动"""
        print(f"\n\033[93mUsing fallback action selection...\033[0m")
        
        if filtered_actions:
            # 选择第一个可用行动
            original_index, fallback_action = filtered_actions[0]
            print(f"\033[96mSending fallback action index: {original_index}\033[0m")
            
            # 🆕 Send just the action index instead of full action details
            await self.send_message({
                'type': 'action',
                'action': str(original_index)  # Send only the action index as string
            })
        else:
            # 发送空行动
            await self.send_message({
                'type': 'action',
                'action': None
            })
            print("\033[96mSent empty action (no alternatives available)\033[0m")

    async def intelligent_fallback_decision(self, playable_actions_data):
        """智能后备决策"""
        # 行动优先级评分
        action_priorities = {
            'CONFIRM_TRADE': 100,  # 最高优先级
            'ACCEPT_TRADE': 90,
            'BUILD_SETTLEMENT': 80,
            'BUILD_CITY': 75,
            'BUILD_ROAD': 70,
            'BUY_DEVELOPMENT_CARD': 60,
            'OFFER_TRADE': 50,
            'MARITIME_TRADE': 40,
            'ROLL': 30,
            'END_TURN': 10,
            'REJECT_TRADE': 5,
            'CANCEL_TRADE': 1
        }
        
        best_action = None
        best_score = -1
        
        for action_data in playable_actions_data:
            action_type = action_data.get('action_type')
            score = action_priorities.get(action_type, 0)
            
            if score > best_score:
                best_score = score
                best_action = action_data
        
        if best_action:
            print(f"\033[95mIntelligent fallback chose: {best_action.get('action_type')} (score: {best_score})\033[0m")
            return best_action
        
        return None

    def reconstruct_game_from_json(self, game_state_json):
        """从JSON重构游戏状态"""
        try:
            # 解析 JSON 字符串（如果需要）
            if isinstance(game_state_json, str):
                game_data = json.loads(game_state_json)
            else:
                game_data = game_state_json
            
            # 创建基础的 Game 对象（不初始化）
            from catanatron.game import Game
            from catanatron.models.player import Color
            from catanatron.players.llm import LLMPlayer
            
            # 创建玩家列表
            colors = game_data.get('colors', ['RED', 'BLUE', 'WHITE', 'ORANGE'])
            players = []
            for color_str in colors:
                color = Color[color_str]
                # 创建 LLM 玩家作为占位符
                player = LLMPlayer(color)
                players.append(player)
            
            # 创建游戏对象（使用初始化）
            game = Game(players=players, initialize=True)
            
            # 設置基本遊戲屬性
            if 'current_color' in game_data:
                current_color_str = game_data['current_color']
                if current_color_str:
                    current_color = Color[current_color_str]
                    # 設置當前玩家
                    game.state.current_player_index = colors.index(current_color_str)
            
            # 設置玩家狀態
            if 'player_state' in game_data:
                game.state.player_state = game_data['player_state']
            
            # 設置資源庫
            if 'resource_freqdeck' in game_data:
                game.state.resource_freqdeck = game_data['resource_freqdeck']
                
            # 設置發展卡庫
            if 'development_listdeck' in game_data:
                game.state.development_listdeck = game_data['development_listdeck']
            
            # 設置當前提示
            if 'current_prompt' in game_data:
                from catanatron.models.enums import ActionPrompt
                prompt_str = game_data['current_prompt']
                if prompt_str:
                    game.state.current_prompt = ActionPrompt[prompt_str]
            
            # 設置可玩動作
            if 'current_playable_actions' in game_data:
                playable_actions_data = game_data['current_playable_actions']
                game.state.playable_actions = []
                for action_data in playable_actions_data:
                    try:
                        if isinstance(action_data, list) and len(action_data) >= 3:
                            from catanatron.json import action_from_json
                            action = action_from_json(action_data)
                            game.state.playable_actions.append(action)
                    except Exception as action_error:
                        # 忽略無法解析的動作
                        continue
            
            # 設置其他基本狀態
            if 'is_initial_build_phase' in game_data:
                game.state.is_initial_build_phase = game_data['is_initial_build_phase']
            
            # 基本驗證：確保遊戲對象有效
            if hasattr(game.state, 'colors') and game.state.colors:
                print(f"\033[92mSuccessfully reconstructed game with {len(game.state.colors)} players\033[0m")
                return game
            else:
                print("\033[93mReconstructed game failed validation\033[0m")
                return None
                
        except Exception as e:
            print(f"\033[93mError reconstructing game from JSON: {e}\033[0m")
            import traceback
            traceback.print_exc()
            return None

    async def send_message(self, message: dict):
        """發送訊息給服務器"""
        if self.websocket and self.connected:
            try:
                # 確保消息中的所有內容都是 JSON 可序列化的
                serializable_message = self.make_json_serializable(message)
                await self.websocket.send(json.dumps(serializable_message))
            except Exception as e:
                print(f"\033[91mError sending message: {e}\033[0m")
                self.connected = False

    def make_json_serializable(self, obj):
        """遞歸地將對象轉換為 JSON 可序列化的格式"""
        if hasattr(obj, 'value') and hasattr(obj, 'name'):  # Color 枚舉
            return obj.value
        elif hasattr(obj, 'name'):  # 其他枚舉
            return obj.name
        elif isinstance(obj, dict):
            return {key: self.make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.make_json_serializable(item) for item in obj]
        else:
            return obj

    async def disconnect(self):
        """斷開連接"""
        if self.websocket:
            await self.websocket.close()
        self.connected = False

    def record_trade_proposal(self, trade_value):
        """删除：不再记录交易提议"""
        pass  # 简化为空函数
        
    async def display_resource_changes_enhanced(self, previous, current):
        """显示资源变动（增强版）"""
        print(f"\n\033[95mRESOURCE CHANGES ANALYSIS:\033[0m")
        print(f"{'='*60}")
        
        resource_names = ['WOOD', 'BRICK', 'SHEEP', 'WHEAT', 'ORE'] 
        
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
                        resource = resource_names[i]
                        if diff > 0:
                            player_changes.append(f"+{diff}{resource}")
                        else:
                            player_changes.append(f"{diff}{resource}")
                        player_total_change += abs(diff)
                
                if player_changes:
                    changes_found = True
                    total_changes += player_total_change
                    
                    color_indicator = "\033[92m*\033[0m" if color_str == self.color.value else " "
                    changes_str = " ".join(player_changes)
                    
                    # 根据变动类型显示不同的趋势
                    if player_total_change > 5:
                        trend = "\033[92mGAINED\033[0m"
                    elif any("+" in change and "-" in change for change in player_changes):
                        trend = "\033[94mTRADED\033[0m"
                    else:
                        trend = "\033[93mCHANGED\033[0m"
                    
                    print(f"{color_indicator}{color_str:<8}: {changes_str} ({trend})")
        
        if not changes_found:
            print(f"  \033[94mNo resource changes detected\033[0m")
        
        print(f"{'='*60}")
        
    def can_propose_trade(self, value):
        """简化：总是允许交易提议"""
        return True  # 不再限制交易次数

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
        print(f"\033[93mDebug mode enabled for {color.value}\033[0m")
    
    # 顯示配置信息
    print(f"\033[96mMax trade proposals per resource type: {args.max_trades}\033[0m")
    
    try:
        # 連接並運行
        await client.connect()
    except KeyboardInterrupt:
        print(f"\n\033[93mReceived interrupt signal, shutting down...\033[0m")
        if client.connected:
            await client.disconnect()
        print(f"\033[92mShutdown complete\033[0m")

if __name__ == "__main__":
    import signal
    
    def signal_handler(signum, frame):
        print(f"\n\033[93mReceived signal {signum}, shutting down...\033[0m")
        raise KeyboardInterrupt()
    
    # 設置信號處理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\033[92mProgram terminated by user\033[0m")
