import os
import random
import json
from google import genai
from google.genai import types

# For type hinting
from catanatron.models.enums import (
    Color,
    Resource as ALL_RESOURCES_ENUM,  # Added for use in _format_game_state_for_llm
    SETTLEMENT,
    CITY,
    ActionPrompt,
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


class LLMPlayer(Player):
    """A Catan player agent that uses Google's Gemini LLM.

    It formulates a detailed prompt based on the game state and uses the LLM
    to choose an action from the list of playable actions.
    """

    def __init__(
        self,
        color: Color,
        model_name: str = "gemini-2.5-flash-preview-05-20",
        api_key: str | None = "AIzaSyCxbVjDyqLssYuc4VWqbHK34YDeuCz7_uQ"
    ):
        super().__init__(color, is_bot=True)
        self.model_name = model_name
        try:
            self.api_key = (
                api_key or os.environ.get("GOOGLE_API_KEY")
            )
            if not self.api_key:
                raise ValueError(
                    "Google API Key not found. Set GOOGLE_API_KEY env var "
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

        state_json = json.dumps(game, cls=GameEncoder)
        # print(state)
        print(game.id)


        state = game.state
        board = state.board
        prompt_lines = [self._system_prompt()]
        # print(prompt_lines)
        prompt_lines.append(str(state_json))
        print(str(state_json))

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
        # prompt_lines.append("\n--- BOARD STATE ---")
        # prompt_lines.append(
        #     f"Robber is at tile coordinate: {board.robber_coordinate}"
        # )

        # prompt_lines.append("\nTiles:")
        # for coord, tile_info in board.map.land_tiles.items():
        #     res_name = tile_info.resource if tile_info.resource else "DESERT"
        #     prompt_lines.append(f"  Tile at {coord}:")
        #     prompt_lines.append(f"    Resource={res_name}, DiceNumber={tile_info.number}")

        # # prompt_lines.append("\nPorts:")
        # # found_ports = False
        # # for tile_obj in board.map.tiles.values():
        # #     if isinstance(tile_obj, Port):
        # #         found_ports = True
        # #         current_port = tile_obj
        # #         node_pair_str = "Unknown"
        # #         node_ref_tuple = PORT_DIRECTION_TO_NODEREFS.get(
        # #             current_port.direction
        # #         )
        # #         if node_ref_tuple and len(node_ref_tuple) == 2:
        # #             node1_id = current_port.nodes.get(node_ref_tuple[0])
        # #             node2_id = current_port.nodes.get(node_ref_tuple[1])
        # #             if node1_id is not None and node2_id is not None:
        # #                 node_ids = tuple(sorted((node1_id, node2_id)))
        # #                 node_pair_str = str(node_ids)
        # #         res_name = current_port.resource if current_port.resource else "ANY"
        # #         ratio = 2 if current_port.resource else 3
        # #         prompt_lines.append(f"  Port at nodes {node_pair_str}:")
        # #         prompt_lines.append(f"    Resource={res_name}, Ratio={ratio}:1")
        # # if not found_ports:
        # #     prompt_lines.append("  No ports on the board.")

        # # prompt_lines.append("\nBuildings (Settlements/Cities):")
        # # if not board.buildings:
        # #     prompt_lines.append("  No buildings on the board.")
        # # else:
        # #     for node_id, (owner_color, b_type) in board.buildings.items():
        # #         b_name = "SETTLEMENT" if b_type == SETTLEMENT else "CITY"
        # #         node_c = board.map.nodes[node_id].coordinate
        # #         prompt_lines.append(f"  Node {node_id} (Coord: {node_c}):")
        # #         prompt_lines.append(f"    {b_name} owned by {owner_color.value}")

        # prompt_lines.append("\nRoads:")
        # if not board.roads:
        #     prompt_lines.append("  No roads on the board.")
        # else:
        #     unique_roads = set()
        #     for edge, owner_color in board.roads.items():
        #         sorted_edge = tuple(sorted(edge))
        #         if sorted_edge not in unique_roads:
        #             prompt_lines.append(f"  Road between Node {edge[0]} and Node {edge[1]}:")
        #             prompt_lines.append(f"    Owned by {owner_color.value}")
        #             unique_roads.add(sorted_edge)

        # # --- Player States ---
        # prompt_lines.append("\n--- PLAYER STATES ---")
        # for p_color in state.colors:
        #     p_key = sf.player_key(state, p_color)
        #     is_self = p_color == self.color
        #     you_str = " (YOU)" if is_self else ""
        #     prompt_lines.append(
        #         f"\nPlayer {p_color.value} ({p_key}){you_str}: "
        #     )

        #     # Resources
        #     player_resource_counts = sf.get_player_freqdeck(state, p_color)
        #     res_counts_strs = []
        #     for i, res_name_str in enumerate(ALL_RESOURCES_ENUM):
        #         res_counts_strs.append(f"{res_name_str}: {player_resource_counts[i]}")
        #     resources_str = ', '.join(res_counts_strs)
        #     prompt_lines.append(f"  Resources: {resources_str}")

        #     # Development Cards
        #     # dev_owned_strs = []
        #     # dev_played_strs = []
        #     # for dev_card in DevelopmentCard: # DevelopmentCard is the list of enums
        #     #     dev_name = dev_card.value # e.g. "KNIGHT"
        #     #     owned_count = sf.get_dev_cards_in_hand(state, p_color, dev_name)
        #     #     if owned_count > 0:
        #     #         dev_owned_strs.append(f"{dev_name}: {owned_count}")
        #     #     played_count = sf.get_played_dev_cards(state, p_color, dev_name)
        #     #     if played_count > 0:
        #     #         dev_played_strs.append(f"{dev_name}: {played_count}")
        #     # dev_owned_final_str = (
        #     #     ', '.join(dev_owned_strs) if dev_owned_strs else 'None'
        #     # )
        #     # prompt_lines.append(f"  Dev Cards (In Hand): {dev_owned_final_str}")
        #     # dev_played_final_str = (
        #     #     ', '.join(dev_played_strs) if dev_played_strs else 'None'
        #     # )
        #     # prompt_lines.append(f"  Dev Cards (Played): {dev_played_final_str}")
        #     # knights_played = sf.get_played_dev_cards(state, p_color, "KNIGHT")
        #     # prompt_lines.append(f"  Knights Played (total): {knights_played}")

        #     # Victory Points
        #     vps = sf.get_visible_victory_points(state, p_color)
        #     prompt_lines.append(f"  Public Victory Points: {vps}")
        #     if is_self:
        #         actual_vps = sf.get_actual_victory_points(state, p_color)
        #         prompt_lines.append(
        #             f"  Actual Victory Points (incl. hidden): {actual_vps}"
        #         )

        #     # Pieces and Status (some still direct access)
        #     roads_avail = state.player_state.get(f'{p_key}_ROADS_AVAILABLE', 0)
        #     prompt_lines.append(f"  Roads Available: {roads_avail}")
        #     settle_avail = state.player_state.get(f'{p_key}_SETTLEMENTS_AVAILABLE', 0)
        #     prompt_lines.append(f"  Settlements Available: {settle_avail}")
        #     cities_avail = state.player_state.get(f'{p_key}_CITIES_AVAILABLE', 0)
        #     prompt_lines.append(f"  Cities Available: {cities_avail}")
        #     p_longest_road = sf.get_longest_road_length(state, p_color)
        #     prompt_lines.append(
        #         f"  Longest Road (personal length): {p_longest_road}"
        #     )
        #     has_road_trophy = sf.get_longest_road_color(state) == p_color
        #     prompt_lines.append(
        #         f"  Has Longest Road Trophy: {has_road_trophy}"
        #     )
        #     largest_army_holder, _ = sf.get_largest_army(state)
        #     has_army_trophy = largest_army_holder == p_color
        #     prompt_lines.append(
        #         f"  Has Largest Army Trophy: {has_army_trophy}"
        #     )
        #     has_rolled = sf.player_has_rolled(state, p_color)
        #     prompt_lines.append(f"  Has Rolled This Turn: {has_rolled}")
        #     dev_card_played_key = (
        #         f"{p_key}_HAS_PLAYED_DEVELOPMENT_CARD_IN_TURN"
        #     )
        #     has_played_dev = state.player_state.get(dev_card_played_key, False)
        #     prompt_lines.append(
        #         f"  Has Played Dev Card This Turn: {has_played_dev}"
        #     )

        # # --- Global Game Status ---
        # prompt_lines.append("\n--- GLOBAL GAME STATUS ---")
        # longest_road_holder_color = sf.get_longest_road_color(state)
        # road_holder_str = longest_road_holder_color.value if longest_road_holder_color else 'None'
        # prompt_lines.append(
        #     f"Longest Road: Held by {road_holder_str}, "
        #     f"Length: {board.road_length}" # board.road_length is global
        # )
        # largest_army_color, largest_army_val = sf.get_largest_army(state)
        # army_holder_str = largest_army_color.value if largest_army_color else 'None'
        # part1 = f"Largest Army: Held by {army_holder_str}, "
        # size_value_as_string = f"{largest_army_val or 0}"
        # part2 = "Size: " + size_value_as_string
        # text_for_prompt = part1 + part2
        # prompt_lines.append(text_for_prompt)
        # prompt_lines.append(
        #     f"Development cards left in deck: {len(state.development_listdeck)}"
        # )
        # # bank_res_list = [
        # #     f"{Resource(i).name}: {count}" # Assuming Resource(i) works if enums.RESOURCES is used as a map key
        # #     for i, count in enumerate(state.resource_freqdeck)
        # # ]
        # # bank_resources_str = ', '.join(bank_res_list)
        # # prompt_lines.append(f"Resources in Bank: {bank_resources_str}")

        # # Current Game Flags / Phases
        # prompt_lines.append("\nCurrent Game Flags:")
        # prompt_lines.append(
        #     f"  Is Initial Build Phase: {state.is_initial_build_phase}"
        # )
        # prompt_lines.append(
        #     f"  Is Discarding Phase (due to 7 roll): {state.is_discarding}"
        # )
        # prompt_lines.append(
        #     f"  Is Moving Knight/Robber: {state.is_moving_knight}"
        # )
        # prompt_lines.append(
        #     f"  Is Road Building (dev card): {state.is_road_building}, "
        #     f"Free Roads Left: {state.free_roads_available}"
        # )

        # if state.is_resolving_trade:
        #     prompt_lines.append("\nTrade Resolution Active:")
        #     offered_list = [
        #         ALL_RESOURCES_ENUM[j] # Use string from ALL_RESOURCES_ENUM
        #         for j, count in enumerate(state.current_trade[:5])
        #         if count > 0 for _ in range(count)
        #     ]
        #     asking_list = [
        #         ALL_RESOURCES_ENUM[j] # Use string from ALL_RESOURCES_ENUM
        #         for j, count in enumerate(state.current_trade[5:10])
        #         if count > 0 for _ in range(count)
        #     ]
        #     offered_str = ', '.join(offered_list)
        #     asking_str = ', '.join(asking_list)
        #     init_color_val = state.current_trade[10]
        #     init_str = (
        #         f"Player {Color(init_color_val).value}"
        #         if isinstance(init_color_val, Color)
        #         else f"Player index {init_color_val}"
        #     )
        #     prompt_lines.append(
        #         f"  Trade Offer by {init_str}: Offers [{offered_str}], "
        #         f"Asks For: [{asking_str}]"
        #     )
        #     acceptees_list = [
        #         state.colors[i].value for i, accepted
        #         in enumerate(state.acceptees) if accepted
        #     ]
        #     acceptees_str = (
        #         ', '.join(acceptees_list) if acceptees_list else 'None'
        #     )
        #     prompt_lines.append(f"  Players who accepted: {acceptees_str}")

        # --- Playable Actions ---
        prompt_lines.append("\n--- AVAILABLE ACTIONS FOR YOU ---")
        if not playable_actions:
            prompt_lines.append("  No actions available.")
        else:
            for i, action in enumerate(playable_actions):
                val_str = str(action.value)
                if action.action_type == ActionType.OFFER_TRADE and \
                   action.value and len(action.value) >= 10:
                    assert False, action.value
                    off_res = [
                        ALL_RESOURCES_ENUM[j] for j, count
                        in enumerate(action.value[:5]) if count > 0
                        for _ in range(count)
                    ]
                    ask_res = [
                        ALL_RESOURCES_ENUM[j] for j, count
                        in enumerate(action.value[5:10]) if count > 0
                        for _ in range(count)
                    ]
                    val_str = (
                        f"Offer: [{', '.join(off_res)}], "
                        f"Ask: [{', '.join(ask_res)}]"
                    )
                elif action.action_type in [
                    ActionType.ACCEPT_TRADE, ActionType.REJECT_TRADE,
                    ActionType.CONFIRM_TRADE
                ] and action.value and len(action.value) >= 10:
                    off_res = [
                        ALL_RESOURCES_ENUM[j] for j, count
                        in enumerate(action.value[:5]) if count > 0
                        for _ in range(count)
                    ]
                    ask_res = [
                        ALL_RESOURCES_ENUM[j] for j, count
                        in enumerate(action.value[5:10]) if count > 0
                        for _ in range(count)
                    ]
                    partner_val = (
                        action.value[-1] if len(action.value) > 10 else
                        "(Self/Bank for maritime)"
                    )
                    partner_str = (
                        f" with Player {Color(partner_val).value}"
                        if isinstance(partner_val, Color)
                        else str(partner_val)
                    )
                    confirm_partner_str = (
                        partner_str if action.action_type ==
                        ActionType.CONFIRM_TRADE else ''
                    )
                    offer_details = f"Offer:[{', '.join(off_res)}]"
                    ask_details = f"Ask:[{', '.join(ask_res)}]"
                    val_str = (
                        f"Trade Offer: {offer_details}, {ask_details}{confirm_partner_str}"
                    )
                    if len(val_str) > 60:
                        val_str = (
                            f"Trade Offer: {offer_details}, \n"
                            f"             {ask_details}{confirm_partner_str}"
                        )
                elif action.action_type == ActionType.MARITIME_TRADE and \
                     action.value and len(action.value) == 2:
                    give_res_idx = action.value[0]
                    rec_res_idx = action.value[1]
                    val_str = f"Give {ALL_RESOURCES_ENUM[give_res_idx]}, Receive {ALL_RESOURCES_ENUM[rec_res_idx]}"
                elif action.action_type == ActionType.MOVE_ROBBER and \
                     action.value and len(action.value) == 2:
                    tile_c = action.value[0]
                    victim_c = (
                        action.value[1].value if action.value[1]
                        else "No one / Self"
                    )
                    val_str = (
                        f"Move robber to tile {tile_c}, Steal from: {victim_c}"
                    )
                elif action.action_type == ActionType.PLAY_MONOPOLY and \
                     action.value is not None:
                    val_str = f"Declare Monopoly on {action.value}"
                elif action.action_type == ActionType.PLAY_YEAR_OF_PLENTY and \
                     action.value and len(action.value) == 2:
                    res1_idx = action.value[0]
                    res2_idx = action.value[1]
                    val_str = f"Take {res1_idx} and {res2_idx} from bank"

                prompt_lines.append(f"  {i}: Type={action.action_type.name},")
                if '\n' in val_str:
                    value_parts = val_str.split('\n')
                    prompt_lines.append(f"       Value={value_parts[0]}")
                    for part in value_parts[1:]:
                        prompt_lines.append(f"              {part.lstrip()}")
                else:
                    prompt_lines.append(f"       Value={val_str}")

        prompt_lines.append(
            "\nBased on the game state and your strategic goals, "
        )
        prompt_lines.append(
            "which action number from the list above do you choose?"
        )
        prompt_lines.append(
            "Respond with ONLY the integer number of your chosen action."
        )
        prompt_lines.append(
            "For example, if you choose action 0, respond with '0'."
        )

        final_prompt = "\n".join(prompt_lines)
        print("--- PROMPT FOR LLM ---")
        print(final_prompt)
        print("----------------------")
        return final_prompt

    def _parse_llm_response(self, response_text: str, playable_actions: list[Action]) -> Action | None:
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

        if len(playable_actions) == 1:
            # print(f"LLM {self.color.value}: Single action: {playable_actions[0]}")
            return playable_actions[0]

        prompt = self._format_game_state_for_llm(game, playable_actions)
        
        try:
            print(
                f"LLMAgent for {self.color.value}: Sending prompt to "
                f"Gemini model {self.model_name}..."
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_budget=1024
                    )
                )
            )   
            for part in response.candidates[0].content.parts:
                if not part.text:
                    continue
                if part.thought:
                    print("Thought summary:")
                    print(part.text)
                    print()
                else:
                    print("Answer:")
                    print(part.text)
                    print()
            llm_response_text = response.text
            print(f"LLM {self.color.value}: RX response: '{llm_response_text}'")
        except Exception as e:
            print(
                f"LLMAgent for {self.color.value}: Error calling Gemini API: {e}. "
                f"Defaulting to random action."
            )
            return random.choice(playable_actions)
        
        chosen_action = self._parse_llm_response(llm_response_text, playable_actions)
        # print(f"LLM {self.color.value} chose action: {chosen_action}")
        return chosen_action

    def __repr__(self):
        return super().__repr__() + f" (LLM: {self.model_name})"

    def _system_prompt(self):
        prompt = """
# Settlers of Catan - Optimal Strategy System Prompt

You are an expert Catan player with deep strategic knowledge. Follow these core principles and strategies:

## GAME OVERVIEW
- **Objective**: First to 10 victory points wins
- **Victory Points Sources**: Settlements (1), Cities (2), Longest Road (2), Largest Army (2), Development Cards (1 each)
- **Resources**: Brick, Lumber, Wool, Grain, Ore (numbers 2-12, avoid 2 and 12)

## INITIAL PLACEMENT STRATEGY

### First Settlement Placement (Priority Order):
1. **Target 6 and 8 first** - These roll most frequently (5/36 probability each)
2. **Secure resource diversity** - Aim for 4-5 different resources across your two settlements
3. **Consider ports strategically** - 3:1 ports are valuable, 2:1 ports are excellent if you can produce that resource
4. **Block opponents** - Deny prime spots, especially if they're going for similar strategies

### Second Settlement Placement:
1. **Complete resource collection** - Ensure access to all 5 resources if possible
2. **Focus on high-probability numbers** - 6, 8, then 5, 9, then 4, 10
3. **Consider development card strategy** - If heavy on Ore/Grain, plan for dev card focus

### Road Placement:
- **Always consider longest road potential** - Plan 2-3 moves ahead
- **Block opponents' expansion** - Cut off their longest road or best expansion spots
- **Secure expansion routes** - Ensure you can reach your planned third settlement

## RESOURCE MANAGEMENT

### Trading Principles:
1. **Trade at 3:1 or better ratios when possible**
2. **Avoid helping leaders** - Don't trade resources that help someone close to winning
3. **Create scarcity** - Hoard resources others need if you're ahead
4. **Time trades strategically** - Trade just before your turn for maximum benefit

### Resource Priority by Game Phase:
**Early Game**: Lumber + Brick (settlements and roads)
**Mid Game**: Ore + Grain (cities and development cards)
**Late Game**: Depends on path to victory

## DEVELOPMENT CARD STRATEGY

### When to Buy Development Cards:
- **You have excess Ore/Grain** consistently
- **Building is blocked** by robber or lack of good spots
- **Racing for Largest Army** (need 3+ knights)
- **Late game** when you need that final victory point

### Development Card Priorities:
1. **Knights** - Control robber, work toward Largest Army
2. **Victory Points** - Hidden points for surprise wins
3. **Year of Plenty/Monopoly** - Situational but powerful
4. **Road Building** - Great for surprise Longest Road

## ROBBER STRATEGY

### Robber Placement Priorities:
1. **Block the current leader's** best production
2. **Target players with many cards** (7+ cards)
3. **Block key resources** you need to deny
4. **Avoid blocking yourself** from future trades

### When You Roll 7:
- **Discard optimally** - Keep building materials, trade materials
- **Target hand sizes strategically** - Steal from players with many cards
- **Consider board position** - Sometimes blocking production > stealing cards

## MID-TO-LATE GAME TRANSITIONS

### Path to Victory Assessment:
**Settlement/City Victory**: 
- Need good expansion spots and consistent production
- Focus on Ore/Grain for cities

**Development Card Victory**:
- Need steady Ore/Grain production
- Build toward Largest Army + hidden VP cards

**Longest Road Victory**:
- Need Lumber/Brick production
- Plan route carefully, build roads in bursts

### Timing Critical Moves:
- **Save resources** before your turn to avoid robber losses
- **Build in bursts** to surprise opponents
- **Count victory points** obsessively in late game
- **Watch for surprise victories** - hidden development cards

## ADVANCED TACTICAL CONCEPTS

### Card Counting:
- **Track development cards** - 25 total (14 knights, 5 VP, 2 each utility)
- **Monitor resource depletion** - Especially cities (4 total) and settlements (5 total)
- **Count opponent victory points** - Including likely hidden dev cards

### Psychological Warfare:
- **Misdirection** - Don't telegraph your strategy too obviously
- **Negotiation** - Create mutually beneficial trades, but always with your benefit prioritized
- **Threat assessment** - Identify and communicate about the current leader

### Endgame Principles:
- **Deny leader resources** through trading embargoes
- **Form temporary alliances** against the leader
- **Calculate exact paths to victory** - yours and opponents'
- **Save surprise moves** - Road building, development cards for final turn

## COMMON MISTAKES TO AVOID

1. **Over-expanding early** - Don't build settlements without cities
2. **Ignoring development cards** - They're often the margin of victory
3. **Poor robber usage** - Not maximizing its strategic impact
4. **Helping opponents** - Every trade should benefit you more
5. **Tunnel vision** - Always reassess your path to victory

## DECISION-MAKING FRAMEWORK

For each turn, evaluate in this order:
1. **Can I win this turn?** - Check all victory point sources
2. **Can someone else win next turn?** - Block if possible
3. **What's my optimal build?** - Based on current strategy and resources
4. **Who should I trade with?** - Maximize your benefit, minimize theirs
5. **Where should the robber go?** - Maximum strategic impact

Remember: Catan combines strategy, tactics, negotiation, and some luck. Adapt your strategy based on the board, dice rolls, and opponent behavior, but always maintain focus on your path to 10 victory points. 使用繁體中文作為思考時的語言。
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
