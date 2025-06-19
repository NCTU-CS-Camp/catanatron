import os
import random
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# For type hinting
from catanatron.models.enums import (
    Color,
    Resource,
    RESOURCES,  # Use the list instead of the enum for indexing
    SETTLEMENT,
    CITY,
    ActionPrompt,
    DEVELOPMENT_CARDS,
)
from catanatron.models.player import Player
from catanatron.models.actions import (
    Action,
    ActionType,
)
from catanatron import state_functions as sf
from catanatron.models.map import (
    NodeId,
    Port,
    PORT_DIRECTION_TO_NODEREFS,
)

from catanatron.json import GameEncoder

# Import for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from catanatron.game import Game


class LLMPlayer(Player):
    """A Catan player agent that uses Google's Gemini LLM.

    It formulates a detailed prompt based on the game state and uses the LLM
    to choose an action from the list of playable actions.
    """

    def __init__(
        self,
        color: Color,
        model_name: str = "gemini-2.5-flash-preview-04-17",
        api_key: str | None = None
    ):
        super().__init__(color, is_bot=True)
        self.model_name = model_name
        try:
            self.api_key = (
                api_key or os.environ.get("GOOGLE_API_KEY")
            )
            if not self.api_key:
                raise ValueError(
                    "Google API Key not found. Set GOOGLE_API_KEY in .env file "
                    "or pass it directly."
                )
            self.client = genai.Client(
                api_key=self.api_key,
            )
            # self.model = genai.GenerativeModel(self.model_name)
            print(f"LLMAgent initialized for color {self.color.value}")
            print(f"Using model {self.model_name}")
        except Exception as e:
            print(
                f"Error initializing LLMAgent for {self.color.value}: {e}"
            )
            print("LLMAgent will fall back to random choices.")
            self.client = None  # Fallback on API key or init error

    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove the unpicklable client attribute
        if 'client' in state:
            del state['client']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # Re-initialize the client attribute
        try:
            if not self.api_key:
                # This case should ideally not happen if api_key was set in __init__
                # and __getstate__ preserved it.
                self.client = None
            else:
                self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            print(f"Error re-initializing LLMAgent client for {self.color.value} during unpickling: {e}")
            self.client = None

    def _format_game_state_for_llm(self, game, playable_actions) -> str:
        """格式化遊戲狀態為 LLM 提示"""
        # 處理 game 為 None 的情況
        if game is None:
            return self._format_actions_only_for_llm(playable_actions)
        
        # 原有的完整遊戲狀態格式化邏輯
        try:
            state_json = json.dumps(game, cls=GameEncoder)
            # print("Game State JSON:")
            # print(state_json)
            # print("-" * 80)
            
            state = game.state
            board = state.board
            prompt_lines = [self._system_prompt()]
            # prompt_lines.append(str(state_json))

            prompt_lines.append(
                f"You are a Catan player, your color is: {self.color.value}."
            )
            prompt_lines.append(
                f"The goal is to reach {game.vps_to_win} victory points."
            )
            prompt_lines.append(f"Current turn number: {state.num_turns}")
            prompt_lines.append(
                f"Player whose turn it is: {state.colors[state.current_turn_index].value}"
            )
            prompt_lines.append(
                f"Player currently making a decision: {state.current_color().value}"
            )
            prompt_lines.append(
                f"Current game phase/prompt: {state.current_prompt.name}"
            )

            # # --- Board State ---
            prompt_lines.append("\n--- BOARD STATE ---")
            prompt_lines.append(
                f"Robber is at tile coordinate: {board.robber_coordinate}"
            )

            prompt_lines.append("\nTiles:")
            for coord, tile_info in board.map.land_tiles.items():
                res_name = tile_info.resource if tile_info.resource else "DESERT"
                prompt_lines.append(f"  Tile at {coord}:")
                prompt_lines.append(f"    Resource={res_name}, DiceNumber={tile_info.number}")

            prompt_lines.append("\nPorts:")
            found_ports = False
            for tile_obj in board.map.tiles.values():
                if isinstance(tile_obj, Port):
                    found_ports = True
                    current_port = tile_obj
                    node_pair_str = "Unknown"
                    node_ref_tuple = PORT_DIRECTION_TO_NODEREFS.get(
                        current_port.direction
                    )
                    if node_ref_tuple and len(node_ref_tuple) == 2:
                        node1_id = current_port.nodes.get(node_ref_tuple[0])
                        node2_id = current_port.nodes.get(node_ref_tuple[1])
                        if node1_id is not None and node2_id is not None:
                            node_ids = tuple(sorted((node1_id, node2_id)))
                            node_pair_str = str(node_ids)
                    res_name = current_port.resource if current_port.resource else "ANY"
                    ratio = 2 if current_port.resource else 3
                    prompt_lines.append(f"  Port at nodes {node_pair_str}:")
                    prompt_lines.append(f"    Resource={res_name}, Ratio={ratio}:1")
            if not found_ports:
                prompt_lines.append("  No ports on the board.")

            prompt_lines.append("\nBuildings (Settlements/Cities):")
            if not board.buildings:
                prompt_lines.append("  No buildings on the board.")
            else:
                for node_id, (owner_color, b_type) in board.buildings.items():
                    b_name = "SETTLEMENT" if b_type == SETTLEMENT else "CITY"
                    prompt_lines.append(f"  Node {node_id}:")
                    prompt_lines.append(f"    {b_name} owned by {owner_color.value}")

            prompt_lines.append("\nRoads:")
            if not board.roads:
                prompt_lines.append("  No roads on the board.")
            else:
                unique_roads = set()
                for edge, owner_color in board.roads.items():
                    sorted_edge = tuple(sorted(edge))
                    if sorted_edge not in unique_roads:
                        prompt_lines.append(f"  Road between Node {edge[0]} and Node {edge[1]}:")
                        prompt_lines.append(f"    Owned by {owner_color.value}")
                        unique_roads.add(sorted_edge)

            # --- Player States ---
            prompt_lines.append("\n--- PLAYER STATES ---")
            for p_color in state.colors:
                p_key = sf.player_key(state, p_color)
                is_self = p_color == self.color
                you_str = " (YOU)" if is_self else ""
                prompt_lines.append(
                    f"\nPlayer {p_color.value} ({p_key}){you_str}: "
                )

                # Resources
                if is_self:
                    player_resource_counts = sf.get_player_freqdeck(state, p_color)
                    res_counts_strs = []
                    for i, res_name_str in enumerate(RESOURCES):
                        res_counts_strs.append(f"{res_name_str}: {player_resource_counts[i]}")
                    resources_str = ', '.join(res_counts_strs)
                    print(f"You have resources: {resources_str}")
                else:
                    total_resources = sum(sf.get_player_freqdeck(state, p_color))
                    prompt_lines.append(
                        f"  Player {p_color.value} has {total_resources} total resources."
                    )

                # Development Cards
                dev_owned_strs = []
                dev_played_strs = []
                for dev_card in DEVELOPMENT_CARDS: # DevelopmentCard is the list of strings
                    dev_name = dev_card # e.g. "KNIGHT"
                    owned_count = sf.get_dev_cards_in_hand(state, p_color, dev_name)
                    if owned_count > 0:
                        dev_owned_strs.append(f"{dev_name}: {owned_count}")
                    played_count = sf.get_played_dev_cards(state, p_color, dev_name)
                    if played_count > 0:
                        dev_played_strs.append(f"{dev_name}: {played_count}")
                dev_owned_final_str = (
                    ', '.join(dev_owned_strs) if dev_owned_strs else 'None'
                )
                prompt_lines.append(f"  Dev Cards (In Hand): {dev_owned_final_str}")
                dev_played_final_str = (
                    ', '.join(dev_played_strs) if dev_played_strs else 'None'
                )
                prompt_lines.append(f"  Dev Cards (Played): {dev_played_final_str}")
                knights_played = sf.get_played_dev_cards(state, p_color, "KNIGHT")
                prompt_lines.append(f"  Knights Played (total): {knights_played}")

                # Victory Points
                vps = sf.get_visible_victory_points(state, p_color)
                prompt_lines.append(f"  Public Victory Points: {vps}")
                if is_self:
                    actual_vps = sf.get_actual_victory_points(state, p_color)
                    prompt_lines.append(
                        f"  Actual Victory Points (incl. hidden): {actual_vps}"
                    )

                # Pieces and Status (some still direct access)
                roads_avail = state.player_state.get(f'{p_key}_ROADS_AVAILABLE', 0)
                prompt_lines.append(f"  Roads Available: {roads_avail}")
                settle_avail = state.player_state.get(f'{p_key}_SETTLEMENTS_AVAILABLE', 0)
                prompt_lines.append(f"  Settlements Available: {settle_avail}")
                cities_avail = state.player_state.get(f'{p_key}_CITIES_AVAILABLE', 0)
                prompt_lines.append(f"  Cities Available: {cities_avail}")
                p_longest_road = sf.get_longest_road_length(state, p_color)
                prompt_lines.append(
                    f"  Longest Road (personal length): {p_longest_road}"
                )
                has_road_trophy = sf.get_longest_road_color(state) == p_color
                prompt_lines.append(
                    f"  Has Longest Road Trophy: {has_road_trophy}"
                )
                largest_army_holder, _ = sf.get_largest_army(state)
                has_army_trophy = largest_army_holder == p_color
                prompt_lines.append(
                    f"  Has Largest Army Trophy: {has_army_trophy}"
                )
                has_rolled = sf.player_has_rolled(state, p_color)
                prompt_lines.append(f"  Has Rolled This Turn: {has_rolled}")
                dev_card_played_key = (
                    f"{p_key}_HAS_PLAYED_DEVELOPMENT_CARD_IN_TURN"
                )
                has_played_dev = state.player_state.get(dev_card_played_key, False)
                prompt_lines.append(
                    f"  Has Played Dev Card This Turn: {has_played_dev}"
                )

            # # --- Global Game Status ---
            prompt_lines.append("\n--- GLOBAL GAME STATUS ---")
            longest_road_holder_color = sf.get_longest_road_color(state)
            try:
                road_holder_str = longest_road_holder_color.value if longest_road_holder_color else 'None'
            except AttributeError as e:
                print(f"Error accessing longest_road_holder_color.value: {e}, type: {type(longest_road_holder_color)}, value: {longest_road_holder_color}")
                road_holder_str = str(longest_road_holder_color) if longest_road_holder_color else 'None'
            prompt_lines.append(
                f"Longest Road: Held by {road_holder_str}, "
                f"Length: {board.road_length}" # board.road_length is global
            )
            largest_army_color, largest_army_val = sf.get_largest_army(state)
            try:
                army_holder_str = largest_army_color.value if largest_army_color else 'None'
            except AttributeError as e:
                print(f"Error accessing largest_army_color.value: {e}, type: {type(largest_army_color)}, value: {largest_army_color}")
                army_holder_str = str(largest_army_color) if largest_army_color else 'None'
            part1 = f"Largest Army: Held by {army_holder_str}, "
            size_value_as_string = f"{largest_army_val or 0}"
            part2 = "Size: " + size_value_as_string
            text_for_prompt = part1 + part2
            prompt_lines.append(text_for_prompt)
            prompt_lines.append(
                f"Development cards left in deck: {len(state.development_listdeck)}"
            )
            # bank_res_list = [
            #     f"{Resource(i).name}: {count}" # Assuming Resource(i) works if enums.RESOURCES is used as a map key
            #     for i, count in enumerate(state.resource_freqdeck)
            # ]
            # bank_resources_str = ', '.join(bank_res_list)
            # prompt_lines.append(f"Resources in Bank: {bank_resources_str}")

            # Current Game Flags / Phases
            prompt_lines.append("\nCurrent Game Flags:")
            prompt_lines.append(
                f"  Is Initial Build Phase: {state.is_initial_build_phase}"
            )
            prompt_lines.append(
                f"  Is Discarding Phase (due to 7 roll): {state.is_discarding}"
            )
            prompt_lines.append(
                f"  Is Moving Knight/Robber: {state.is_moving_knight}"
            )
            prompt_lines.append(
                f"  Is Road Building (dev card): {state.is_road_building}, "
                f"Free Roads Left: {state.free_roads_available}"
            )

            if state.is_resolving_trade:
                prompt_lines.append("\nTrade Resolution Active:")
                offered_list = [
                    RESOURCES[j] # Use string from RESOURCES list
                    for j, count in enumerate(state.current_trade[:5])
                    if count > 0 for _ in range(count)
                ]
                asking_list = [
                    RESOURCES[j] # Use string from RESOURCES list
                    for j, count in enumerate(state.current_trade[5:10])
                    if count > 0 for _ in range(count)
                ]
                offered_str = ', '.join(offered_list)
                asking_str = ', '.join(asking_list)
                init_color_val = state.current_trade[10]
                init_str = (
                    f"Player {Color(init_color_val).value}"
                    if isinstance(init_color_val, Color)
                    else f"Player index {init_color_val}"
                )
                prompt_lines.append(
                    f"  Trade Offer by {init_str}: Offers [{offered_str}], "
                    f"Asks For: [{asking_str}]"
                )
                acceptees_list = [
                    state.colors[i].value for i, accepted
                    in enumerate(state.acceptees) if accepted
                ]
                acceptees_str = (
                    ', '.join(acceptees_list) if acceptees_list else 'None'
                )
                prompt_lines.append(f"  Players who accepted: {acceptees_str}")

            # --- 即時戰術建議 ---
            prompt_lines.append("\n--- 🚨 即時戰術建議 ---")
            
            # 檢查當前分數和建造建議
            your_key = sf.player_key(state, self.color)
            your_vps = sf.get_actual_victory_points(state, self.color)
            your_settlements = len(state.buildings_by_color[self.color][SETTLEMENT])
            your_cities = len(state.buildings_by_color[self.color][CITY])
            your_resources = sf.get_player_freqdeck(state, self.color)
            total_resources = sum(your_resources)
            
            prompt_lines.append(f"你的當前分數: {your_vps}/10")
            prompt_lines.append(f"你的建築: {your_settlements} 村莊, {your_cities} 城市")
            prompt_lines.append(f"你的總資源數: {total_resources}")
            
            # 建造建議
            building_actions = [a for a in playable_actions if a.action_type in [ActionType.BUILD_SETTLEMENT, ActionType.BUILD_CITY]]
            if building_actions:
                prompt_lines.append("🎯 優先考慮: 你可以建造建築！這是得分的主要方式。")
                for action in building_actions:
                    if action.action_type == ActionType.BUILD_SETTLEMENT:
                        prompt_lines.append("  → 建造村莊 (+1分) - 強烈推薦！")
                    elif action.action_type == ActionType.BUILD_CITY:
                        prompt_lines.append("  → 升級城市 (+1分) - 推薦！")
            
            # 交易建議
            trade_actions = [a for a in playable_actions if a.action_type in [ActionType.MARITIME_TRADE, ActionType.OFFER_TRADE]]
            if trade_actions and not building_actions:
                prompt_lines.append("💰 考慮交易: 你無法直接建造，考慮交易獲得建造資源。")
            
            # 資源過多警告
            if total_resources >= 7:
                prompt_lines.append("⚠️  警告: 你有7+張牌，容易被強盜影響。優先建造建築！")
            
            # 分數差距分析
            all_vps = [sf.get_visible_victory_points(state, color) for color in state.colors]
            max_vps = max(all_vps)
            if your_vps < max_vps - 1:
                prompt_lines.append(f"📈 你落後 {max_vps - your_vps} 分，需要加快建造速度！")
            
            # --- 決策指導 ---
            prompt_lines.append("\n--- 🎯 當前局勢即時分析 ---")
            
            # 分析自己的當前狀況
            my_key = sf.player_key(state, self.color)
            my_victory_points = state.player_state.get(f"{my_key}_VICTORY_POINTS", 0)
            my_resources = sf.get_player_freqdeck(state, self.color)
            my_total_resources = sum(my_resources)
            
            # 計算能建造什麼
            can_build_settlement = (my_resources[0] >= 1 and my_resources[1] >= 1 and 
                                   my_resources[2] >= 1 and my_resources[3] >= 1)  # wood, brick, sheep, wheat
            can_build_city = (my_resources[3] >= 2 and my_resources[4] >= 3)  # wheat, ore
            can_build_road = (my_resources[0] >= 1 and my_resources[1] >= 1)  # wood, brick
            can_buy_dev_card = (my_resources[2] >= 1 and my_resources[3] >= 1 and my_resources[4] >= 1)  # sheep, wheat, ore
            
            prompt_lines.append(f"🏆 你的分數: {my_victory_points}/10")
            prompt_lines.append(f"💰 總資源數: {my_total_resources}")
            
            # 建造能力分析
            prompt_lines.append("🏗️ 建造能力分析:")
            if can_build_settlement:
                prompt_lines.append("  ✅ 能建造村莊 - 最高優先級！立即建造！")
            else:
                needed = []
                if my_resources[0] < 1: needed.append("木頭")
                if my_resources[1] < 1: needed.append("磚頭") 
                if my_resources[2] < 1: needed.append("羊毛")
                if my_resources[3] < 1: needed.append("小麥")
                prompt_lines.append(f"  ❌ 無法建造村莊 - 缺少: {', '.join(needed)}")
                
            if can_build_city:
                prompt_lines.append("  ✅ 能建造城市 - 高優先級！")
            else:
                needed = []
                if my_resources[3] < 2: needed.append(f"小麥({2-my_resources[3]})")
                if my_resources[4] < 3: needed.append(f"礦石({3-my_resources[4]})")
                prompt_lines.append(f"  ❌ 無法建造城市 - 缺少: {', '.join(needed)}")
                
            if can_build_road:
                prompt_lines.append("  ✅ 能建造道路")
            else:
                needed = []
                if my_resources[0] < 1: needed.append("木頭")
                if my_resources[1] < 1: needed.append("磚頭")
                prompt_lines.append(f"  ❌ 無法建造道路 - 缺少: {', '.join(needed)}")
                
            if can_buy_dev_card:
                prompt_lines.append("  ✅ 能購買發展卡")
            else:
                needed = []
                if my_resources[2] < 1: needed.append("羊毛")
                if my_resources[3] < 1: needed.append("小麥")
                if my_resources[4] < 1: needed.append("礦石")
                prompt_lines.append(f"  ❌ 無法購買發展卡 - 缺少: {', '.join(needed)}")

            # 威脅評估
            prompt_lines.append("\n⚠️ 對手威脅評估:")
            max_enemy_vp = 0
            leader_color = None
            for p_color in state.colors:
                if p_color != self.color:
                    p_key = sf.player_key(state, p_color)
                    vp = state.player_state.get(f"{p_key}_VICTORY_POINTS", 0)
                    if vp > max_enemy_vp:
                        max_enemy_vp = vp
                        leader_color = p_color
            
            if max_enemy_vp >= 8:
                prompt_lines.append(f"  🚨 緊急威脅！{leader_color.value if leader_color else '對手'}已有{max_enemy_vp}分！")
                prompt_lines.append("  必須立即阻止對手或加速自己的建造！")
            elif max_enemy_vp >= 6:
                prompt_lines.append(f"  ⚠️ 注意威脅：{leader_color.value if leader_color else '對手'}已有{max_enemy_vp}分")
            else:
                prompt_lines.append("  ✅ 暫無緊急威脅，可以專注發展")

            # 資源管理建議
            prompt_lines.append(f"\n💡 資源管理建議:")
            if my_total_resources >= 7:
                prompt_lines.append("  🚨 資源過多！強盜來時要棄牌，快建造建築！")
            if my_total_resources <= 2:
                prompt_lines.append("  📈 資源不足，考慮交易或等待收入")
            
            # 即時決策優先級
            prompt_lines.append("\n🎯 即時決策優先級:")
            if can_build_settlement:
                prompt_lines.append("1. 🏘️ 建造村莊 - 絕對最高優先級！")
                prompt_lines.append("   找到BUILD_SETTLEMENT動作立即選擇！")
            else:
                prompt_lines.append("1. 💱 交易獲得村莊資源 - 最重要目標！")
                
            if can_build_city and my_victory_points >= 3:
                prompt_lines.append("2. 🏛️ 建造城市 - 高優先級！")
            elif can_build_road:
                prompt_lines.append("2. 🛣️ 建造道路 - 為未來村莊做準備")
            else:
                prompt_lines.append("2. 💱 交易獲得建造資源")
                
            prompt_lines.append("3. 🃏 其他行動 - 根據具體情況")

            prompt_lines.append("\n--- 可用動作列表 ---")
            prompt_lines.append("仔細分析每個動作，選擇最符合戰略的:")
            
            for i, action in enumerate(playable_actions):
                action_priority = "🔥"  # Default
                
                if action.action_type == ActionType.BUILD_SETTLEMENT:
                    action_priority = "🔥🔥🔥 最高優先級"
                elif action.action_type == ActionType.BUILD_CITY:
                    action_priority = "🔥🔥 高優先級"
                elif action.action_type == ActionType.BUILD_ROAD:
                    action_priority = "🔥 中等優先級"
                elif action.action_type == ActionType.OFFER_TRADE:
                    if not can_build_settlement and not can_build_city:
                        action_priority = "🔥🔥 高優先級(獲得建造資源)"
                    else:
                        action_priority = "💭 考慮交易價值"
                elif action.action_type == ActionType.BUY_DEVELOPMENT_CARD:
                    if my_total_resources > 7:
                        action_priority = "🔥 防止棄牌"
                    else:
                        action_priority = "💭 低優先級"
                
                # Format action details
                val_str = str(action.value) if action.value is not None else "None"
                if hasattr(action, 'action_type'):
                    if action.action_type == ActionType.BUILD_SETTLEMENT:
                        val_str = f"在節點 {action.value} 建造村莊"
                    elif action.action_type == ActionType.BUILD_CITY:
                        val_str = f"在節點 {action.value} 建造城市"
                    elif action.action_type == ActionType.BUILD_ROAD:
                        val_str = f"在 {action.value} 建造道路"
                    elif action.action_type == ActionType.OFFER_TRADE and \
                         hasattr(action, 'value') and action.value:
                        if len(action.value) >= 10:
                            # OFFER_TRADE uses 10-tuple format: first 5 are offered, last 5 are asked
                            offered_resources = []
                            asked_resources = []
                            
                            # Extract offered resources (first 5 indices)
                            for i in range(5):
                                count = action.value[i]
                                if count > 0:
                                    offered_resources.extend([RESOURCES[i]] * count)
                            
                            # Extract asked resources (last 5 indices)
                            for i in range(5):
                                count = action.value[5 + i]
                                if count > 0:
                                    asked_resources.extend([RESOURCES[i]] * count)
                            
                            offer_details = f"提供:[{', '.join(offered_resources)}]"
                            ask_details = f"要求:[{', '.join(asked_resources)}]"
                            val_str = f"{offer_details}, {ask_details}"
                    elif action.action_type == ActionType.MARITIME_TRADE and \
                         action.value and len(action.value) == 2:
                        give_res_idx = action.value[0]
                        rec_res_idx = action.value[1]
                        val_str = f"給出 {RESOURCES[give_res_idx]}, 獲得 {RESOURCES[rec_res_idx]}"
                    elif action.action_type == ActionType.MOVE_ROBBER and \
                         action.value and len(action.value) >= 2:
                        tile_c = action.value[0]
                        victim = action.value[1]
                        if victim is None:
                            victim_c = "無目標"
                        elif hasattr(victim, 'value'):
                            victim_c = victim.value
                        else:
                            victim_c = str(victim)
                        val_str = f"移動強盜到 {tile_c}, 偷取: {victim_c}"

                prompt_lines.append(f"  {i}: {action_priority}")
                prompt_lines.append(f"      類型={action.action_type.name}")
                prompt_lines.append(f"      詳情={val_str}")
                prompt_lines.append("")

            # 最終指導
            prompt_lines.append("🎯 決策指導總結:")
            prompt_lines.append("優先選擇能建造村莊的動作！")
            prompt_lines.append("如果無法建造，選擇交易來獲得建造資源！")
            prompt_lines.append("記住：積極建造 > 被動等待")
            
            prompt_lines.append(
                "\n基於以上分析，你應該選擇哪個動作編號？"
            )
            prompt_lines.append(
                "請只回答一個整數編號。"
            )
            
            # 添加更強的格式約束
            prompt_lines.append(
                "\n⚠️ 重要：你必須只回答一個整數編號！"
            )
            prompt_lines.append(
                "✅ 正確回答範例: '0', '5', '12'"
            )
            prompt_lines.append(
                "❌ 錯誤回答範例: '我選擇動作5', '動作0看起來不錯', '讓我想想...'"
            )
            prompt_lines.append(
                "\n你選擇哪個動作編號？(只回答數字)"
            )

            final_prompt = "\n".join(prompt_lines)
            return final_prompt
        except Exception as e:
            print(f"Error formatting full game state: {e}")
            # 回退到僅格式化行動
            return self._format_actions_only_for_llm(playable_actions)
    
    def _format_actions_only_for_llm(self, playable_actions) -> str:
        """當遊戲狀態不可用時，僅格式化可用行動"""
        system_prompt = self._system_prompt()
        
        prompt_lines = [
            system_prompt,
            "",
            f"=== TURN FOR {self.color.value} ===",
            "",
            "Available Actions:",
        ]
        
        for i, action in enumerate(playable_actions):
            action_desc = self._format_single_action(action)
            prompt_lines.append(f"  {i}: {action_desc}")
        
        prompt_lines.extend([
            "",
            f"Choose the best action (0-{len(playable_actions)-1}) for {self.color.value}:",
            "Consider the action type and strategic value.",
            "",
            # 添加更強的格式約束
            "CRITICAL: You must respond with ONLY a single integer number.",
            "Examples of CORRECT responses: '0', '5', '12'",
            "Examples of INCORRECT responses: 'I choose action 5', 'Action 0 looks good', 'Let me think...'",
            "",
            "Which action number do you choose? (Respond with ONLY the number)"
        ])
        
        return "\n".join(prompt_lines)
    
    def _format_single_action(self, action) -> str:
        """格式化單個行動的描述"""
        try:
            if action.action_type.name == "BUILD_SETTLEMENT":
                return f"Build Settlement at node {action.value}"
            elif action.action_type.name == "BUILD_CITY":
                return f"Build City at node {action.value}"
            elif action.action_type.name == "BUILD_ROAD":
                return f"Build Road between nodes {action.value}"
            elif action.action_type.name == "BUY_DEVELOPMENT_CARD":
                return "Buy Development Card"
            elif action.action_type.name == "MOVE_ROBBER":
                if len(action.value) >= 3:
                    coord, victim, _ = action.value
                elif len(action.value) >= 2:
                    coord, victim = action.value[0], action.value[1]
                else:
                    coord, victim = action.value[0], None
                if victim is None:
                    victim_str = "No one"
                elif hasattr(victim, 'value'):
                    victim_str = victim.value
                else:
                    victim_str = str(victim)
                return f"Move Robber to {coord}, steal from {victim_str}"
            elif action.action_type.name == "MARITIME_TRADE":
                return f"Maritime Trade: {action.value}"
            elif action.action_type.name == "END_TURN":
                return "End Turn"
            elif action.action_type.name == "ROLL":
                return "Roll Dice"
            elif action.action_type.name == "DISCARD":
                return "Discard Cards (due to 7 roll)"
            else:
                return f"{action.action_type.name}: {action.value}"
        except Exception as e:
            return f"{action.action_type.name}: {str(action.value)}"

    def _parse_llm_response(self, response_text: str, playable_actions: list[Action]) -> Action | None:
        if response_text is None:
            print("LLM response was None. Defaulting to random valid action.")
            return random.choice(playable_actions) if playable_actions else None
            
        try:
            chosen_index = int(response_text.strip())
            if 0 <= chosen_index < len(playable_actions):
                return playable_actions[chosen_index]
            else:
                print(
                    f"LLM chose an invalid index: {chosen_index}. "
                    f"Defaulting to random valid action."
                )
                return random.choice(playable_actions) if playable_actions else None
        except ValueError:
            print(
                f"LLM response was not a valid integer: '{response_text}'. "
                f"Defaulting to random valid action."
            )
            return random.choice(playable_actions) if playable_actions else None
        except Exception as e:
            print(
                f"Error parsing LLM response: {e}. "
                f"Defaulting to random valid action."
            )
            return random.choice(playable_actions) if playable_actions else None

    def decide(self, game: "Game", playable_actions: list[Action]) -> Action | None:
        if not self.client:  # Fallback if model init failed
            print(
                f"LLMAgent for {self.color.value} (FALBACK): "
                f"Choosing randomly due to model init error."
            )
            return random.choice(playable_actions) if playable_actions else None

        if not playable_actions:
            print(
                f"LLMAgent for {self.color.value}: "
                f"No playable actions received."
            )
            return None 

        # if len(playable_actions) == 1:
        #     # print(f"LLM {self.color.value}: Single action: {playable_actions[0]}")
        #     return playable_actions[0]

        prompt = self._format_game_state_for_llm(game, playable_actions)
        
        try:
            print(f"LLMAgent for {self.color.value}: Sending prompt to Gemini model {self.model_name}...")
            # print complete prompt for debugging
            # print(prompt)
            # 配置 thinking 功能（僅支援 2.5 系列模型）
            if "2.5" in self.model_name or "gemini-2.5" in self.model_name:
                # 使用 thinking 功能的配置
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=2048,  # 中等思考預算，適合複雜決策
                            include_thoughts=True  # 包含思考過程
                        ),
                        temperature=0.7,
                        max_output_tokens=4096
                    )
                )
                
                # 打印思考過程（可選，用於調試）
                if hasattr(response, 'candidates') and len(response.candidates) > 0:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'thought') and part.thought and part.text:
                            print(f"LLM {self.color.value} Thinking: {part.text[:200]}...")
                            
            else:
                # 舊版模型使用簡化配置
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=100
                    )
                )
            
            llm_response_text = response.text
            if llm_response_text is None:
                print(f"LLM {self.color.value}: Received empty response from API. Defaulting to random action.")
                return random.choice(playable_actions)
            print(f"LLM {self.color.value}: RX response: '{llm_response_text}'")
            
        except Exception as e:
            print(f"LLMAgent for {self.color.value}: Error calling Gemini API: {e}. Defaulting to random action.")
            return random.choice(playable_actions)
        
        chosen_action = self._parse_llm_response(llm_response_text, playable_actions)
        return chosen_action

    def __repr__(self):
        return super().__repr__() + f" (LLM: {self.model_name})"

    def _system_prompt(self):
        prompt = """
# 🏝️ 卡坦島終極戰略大師系統

你是一位頂級卡坦島AI專家，擁有豐富的遊戲經驗和策略知識。以下是完整的戰略指南：

## 🎯 遊戲目標與勝利條件

### 主要目標：率先達到 10 勝利點！

### 勝利點獲得方式：
- **🏘️ 村莊 (Settlement)**: 每個 +1 分
- **🏛️ 城市 (City)**: 每個 +2 分（村莊升級）
- **🛣️ 最長道路**: +2 分（需要連續5+段道路，且比其他玩家長）
  **⚠️ 重要：最長道路只有第一個達到的玩家能獲得！先到先得！**
- **⚔️ 最大軍隊**: +2 分（需要使用3+張騎士卡，且比其他玩家多）
- **🏆 勝利點發展卡**: 每張 +1 分（隱藏分數）

### 📊 分數追蹤提醒：
- 時刻計算自己和對手的**公開分數**
- 警惕對手可能擁有的**隱藏勝利點卡**
- 當有人達到8-9分時，必須阻止其獲勝

## 🏗️ 建築戰略核心（最重要！）

### 🚨 核心理念：積極擴張，持續建造
**永遠記住：卡坦島是建造遊戲，不是資源囤積遊戲！**

### 建造成本一覽：
- **🏘️ 村莊**: 1木頭 + 1磚頭 + 1羊毛 + 1小麥
- **🏛️ 城市**: 2小麥 + 3礦石（必須升級已有村莊）
- **🛣️ 道路**: 1木頭 + 1磚頭
- **🃏 發展卡**: 1羊毛 + 1小麥 + 1礦石

### 🏠 村莊建設至上原則

🚨 **核心戰略重點：村莊是得分的主要來源！必須優先多蓋村莊，而不是一直建道路！**

### 📍 起始位置選擇原則：
- **🎲 高頻數字**: 優先選擇6、8附近的位置
- **💎 資源多樣性**: 確保能取得不同類型資源  
- **🚢 港口考量**: 考慮是否能連接到有用的港口
- **🛣️ 擴展潛力**: 選擇有後續建造空間的位置
- **🎯 慎選起點**: 起始位置決定整局發展方向！

### 建造優先級策略：

#### 🥇 第一優先：建造村莊
- **最低目標**: 4個村莊（4分基礎）
- **理想目標**: 5個村莊（5分，非常安全）
- **位置選擇**: 優先高產出數字（6、8、5、9、4、10）
- **資源多樣性**: 確保能獲得所有5種資源
- **港口考量**: 優先搶佔有用的港口位置

#### 🥈 第二優先：升級城市
- **時機**: 當已有3-4個村莊且礦石充足時
- **選擇**: 升級產出最好的村莊位置
- **效益**: 每個城市相當於2個村莊的資源產出

#### 🥉 第三優先：道路建設
🚨 **道路建設重要原則**：
- **⛔ 避免只建道路不建村莊！** 道路本身不給分數！
- **🎯 建造導向**: 道路必須為了建造新村莊而存在
- **🏆 最長道路競爭**: 只有第一個達到的人能獲得獎勵！
- **🗺️ 戰略規劃**: 為了搶佔關鍵建造點而建道路
- **阻擋對手**: 切斷對手的擴張路線

#### 🎴 第四優先：發展卡
- **購買時機**: 無法建造建築且資源過多時
- **騎士卡**: 用於強盜控制和最大軍隊
- **勝利點卡**: 隱藏分數，關鍵時刻驚喜獲勝
- **其他卡**: 豐年卡和壟斷卡用於資源獲取

## 📈 階段性戰略

### 🌱 開局階段（0-3分）
**重點：快速擴張，建立資源基礎**
- 建造2-3個村莊作為核心
- 選擇多樣化資源的位置
- 優先考慮高頻率骰子數字
- 建設道路連接優質建造點

### ⚡ 中期階段（4-6分）
**重點：優化產出，追求特殊分數**
- 繼續建造村莊（目標5個）
- 開始升級城市（特別是礦石豐富時）
- 考慮追求最長道路或最大軍隊
- 積極參與交易，優化資源配置

### 🏁 衝刺階段（7-9分）
**重點：確保獲勝，阻止對手**
- 計算最快獲勝路線
- 積極使用發展卡
- 阻止其他玩家獲勝
- 隱藏真實分數（勝利點卡）

## 🎲 骰子與數字戰略

### 🎯 最優數字選擇：
1. **6和8**: 最高頻率（各5/36機率）
2. **5和9**: 次高頻率（各4/36機率）
3. **4和10**: 中等頻率（各3/36機率）
4. **3和11**: 較低頻率（各2/36機率）
5. **2和12**: 最低頻率（各1/36機率）

### 📊 統計思維：
- 優先在6和8上建造
- 避免在2和12上過度投資
- 平衡風險與收益

## 💰 交易大師戰略

### 🚨 重要限制：每回合最多只能提出交易2次！
**慎重選擇你的交易提案 - 機會有限，必須精確計算！**

### 🤝 國內交易原則：
1. **次數限制**: 每回合最多提出2次交易 - 必須慎選時機和對象
2. **互利共贏**: 確保交易對你更有利
3. **避免幫助領先者**: 檢查對手分數和建造能力
4. **建造導向**: 只為了建造建築而交易
5. **資源比率**: 了解標準交易比率（4:1）

### 🏪 港口交易運用：
- **通用港口**: 3:1交易任意資源
- **專門港口**: 2:1交易特定資源
- **港口控制**: 優先搶佔對應資源的專門港口

### 📋 交易檢查清單：
- **🔢 次數確認**: 這回合我還剩幾次交易機會？（最多2次）
- 我能通過這次交易建造什麼？
- 對手能通過這次交易建造什麼？
- 這個交易對誰更有利？
- 有沒有更好的交易選擇？
- 這是我最優先需要的交易嗎？

## 🏴‍☠️ 強盜戰術運用

### 🎯 強盜放置策略：
1. **阻擋領先者**: 放在領先者最重要的資源地塊
2. **最大收益**: 選擇影響最多玩家的地塊
3. **資源枯竭**: 針對對手缺少的關鍵資源
4. **保護自己**: 避免放在自己重要的地塊上

### 💳 偷牌策略：
- **手牌最多**: 優先偷手牌最多的玩家
- **領先玩家**: 阻礙領先者的發展
- **獲得情報**: 了解對手的資源狀況

## 🃏 發展卡高級戰術

### ⚔️ 騎士卡運用：
- **強盜控制**: 將強盜移到對對手最不利的位置
- **最大軍隊**: 需要比其他玩家多使用騎士卡
- **偷牌價值**: 從手牌多的玩家偷取資源

### 🌾 豐年卡策略：
- **關鍵時刻**: 當需要特定資源建造時使用
- **骰子選擇**: 選擇你控制最多地塊的數字
- **時機掌握**: 在其他玩家回合前使用

### 💎 壟斷卡運用：
- **資源收集**: 壟斷你需要大量的資源
- **情報收集**: 了解其他玩家的資源狀況
- **關鍵阻擋**: 壟斷對手需要的關鍵資源

## ⚡ 即時決策框架

### 每回合必檢項目：
1. **🏆 勝利檢查**: 我能這回合獲勝嗎？
2. **🚨 威脅評估**: 有人下回合可能獲勝嗎？
3. **🏗️ 建造能力**: 我能建造什麼建築？
4. **💱 交易需求**: 需要什麼資源來建造？
5. **🏴‍☠️ 強盜決策**: 強盜應該放在哪裡？

### 資源管理檢查：
- **手牌上限**: 超過7張牌要準備棄牌
- **建造資源**: 優先保留建造需要的資源
- **交易價值**: 評估資源的交易價值

### 戰術優先級：
1. **能建造村莊？** → 立即建造！
2. **能升級城市？** → 如果已有3+村莊，考慮升級
3. **能建造關鍵道路？** → 為了連接建造點
4. **資源過多？** → 建造任何可能的建築或購買發展卡

## 🎯 高級戰略思維

### 🧠 心理戰術：
- **隱藏意圖**: 不要過早暴露你的戰略
- **虛實結合**: 有時候故意表現出對某個資源的需求
- **觀察對手**: 分析對手的建造模式和喜好

### 📊 數據分析：
- **骰子統計**: 記錄哪些數字出現頻率高/低
- **資源流動**: 觀察哪些資源在市場上稀缺
- **建造速度**: 比較各玩家的建造進度

### 🎭 適應性策略：
- **靈活調整**: 根據骰子運氣調整戰略
- **機會抓取**: 抓住對手的戰略失誤
- **風險管理**: 在激進擴張和穩健發展間平衡

## 🚨 常見致命錯誤（絕對避免！）

### ❌ 建造失誤：
1. **🚨 只建道路不建村莊** - 這是最致命的錯誤！道路不給分數！
2. **過度囤積資源** - 有資源不建造建築
3. **忽視村莊建設** - 村莊是主要得分來源，要多蓋！
4. **過早追求城市** - 沒有足夠村莊基礎
5. **盲目道路建設** - 不是為了建造點而建道路
6. **起點選擇失誤** - 沒有慎選起始位置，影響整局發展

### ❌ 交易失誤：
1. **幫助領先者** - 讓領先的玩家更容易獲勝
2. **無意義交易** - 交易後仍無法建造任何建築
3. **忽視港口** - 不善用港口交易優勢

### ❌ 戰術失誤：
1. **強盜濫用** - 強盜放置沒有戰略考量
2. **發展卡誤用** - 在錯誤的時機使用發展卡
3. **缺乏大局觀** - 只關注自己，忽視對手威脅

## 🎓 大師級建議

### 💡 進階技巧：
1. **資源組合**: 記住各種建築的資源需求組合
2. **機率計算**: 利用骰子機率優化位置選擇
3. **對手分析**: 分析對手的戰略模式和弱點
4. **時機掌握**: 知道何時激進，何時保守

### 🏆 獲勝心法：
**建造為王**: 永遠優先建造建築
**靈活應變**: 根據局勢調整戰略
**控制節奏**: 掌握遊戲發展的主動權
**細節制勝**: 注意每一個決策的長期影響

### 🔥 終極原則：
**永遠記住：卡坦島的勝負在於村莊數量和位置，不在於道路長度和資源數量！**
**🏠 村莊 > 🛣️ 道路 > 💎 資源囤積**

---

現在，基於以上完整戰略指南，分析當前局勢並做出最佳決策。每個決策都應該有明確的戰略理由，並考慮長期和短期的收益。加油，展現你的卡坦島大師實力！🏆
        """
        return prompt


# Example usage (testing; normally instantiated by game engine)
if __name__ == '__main__':
    # This is a mock setup. You'd need a proper Game and State object.
    class MockGame:
        def __init__(self):
            self.vps_to_win = 10
            self.state = MockState()

    class MockState:
        def __init__(self):
            self.current_prompt = ActionType.ROLL  # Example
            self.current_turn_index = 0
            self.colors = [Color.RED, Color.BLUE, Color.WHITE]
            self.board = MockBoard()
            self.player_state = {
                'P0_VICTORY_POINTS': 2, 'P0_KNIGHTS_PLAYED': 0,
                'P1_VICTORY_POINTS': 1, 'P1_KNIGHTS_PLAYED': 0,
                'P2_VICTORY_POINTS': 3, 'P2_KNIGHTS_PLAYED': 0,
            }
            self.dev_cards = [1] * 10  # Mock dev cards
            self.largest_army_player = None
            self.largest_army_size = 0
        def current_color(self):
            return self.colors[self.current_turn_index]

    class MockBoard:
        def __init__(self):
            self.robber_coord = (0, 0)
            self.longest_road_player = None
            self.longest_road_length = 0
    
    # Mock functions removed; direct state access now used in main class.
    # For the example to run, you would need to fully mock
    # state.player_state with all keys
    # from PLAYER_INITIAL_STATE (in catanatron.state) for each player.
    # And mock state.board.map.land_tiles, state.board.map.ports, etc.
    # This example is now significantly more complex to mock
    # due to detailed state access.

    # Ensure GOOGLE_API_KEY is set in your environment to run this example
    if os.environ.get("GOOGLE_API_KEY"):
        llm_player = LLMPlayer(Color.RED)
        mock_game = MockGame()
        mock_actions = [
            Action(Color.RED, ActionType.ROLL, None),
            Action(Color.RED, ActionType.BUILD_ROAD, ((0, 0), (1, 1))),
        ]
        chosen = llm_player.decide(mock_game, mock_actions)
        print(f"Test LLM Player chose: {chosen}")
    else:
        print("Skipping LLMPlayer example: GOOGLE_API_KEY not set.")
