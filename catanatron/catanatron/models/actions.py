"""
Move-generation functions (these return a list of actions that can be taken
by current player). Main function is generate_playable_actions.
"""

import operator as op
from functools import reduce
from typing import Any, Dict, List, Set, Tuple, Union

from catanatron.models.decks import (
    CITY_COST_FREQDECK,
    ROAD_COST_FREQDECK,
    SETTLEMENT_COST_FREQDECK,
    freqdeck_can_draw,
    freqdeck_contains,
    freqdeck_count,
    freqdeck_from_listdeck,
)
from catanatron.models.enums import (
    RESOURCES,
    Action,
    ActionPrompt,
    ActionType,
    BRICK,
    ORE,
    FastResource,
    SETTLEMENT,
    SHEEP,
    WHEAT,
    WOOD,
)
from catanatron.state_functions import (
    get_player_buildings,
    get_player_freqdeck,
    player_can_afford_dev_card,
    player_can_play_dev,
    player_has_rolled,
    player_key,
    player_num_resource_cards,
    player_resource_freqdeck_contains,
)


def generate_playable_actions(state):
    """生成所有可用行動"""
    actions = []
    
    color = state.current_color()
    action_prompt = state.current_prompt

    if action_prompt == ActionPrompt.BUILD_INITIAL_SETTLEMENT:
        return settlement_possibilities(state, color, True)
    elif action_prompt == ActionPrompt.BUILD_INITIAL_ROAD:
        return initial_road_possibilities(state, color)
    elif action_prompt == ActionPrompt.MOVE_ROBBER:
        return robber_possibilities(state, color)
    elif action_prompt == ActionPrompt.PLAY_TURN:
        actions = []

        if not player_has_rolled(state, color):
            actions.append(Action(color, ActionType.ROLL, None))
            return actions  # must roll first

        # Build city (over existing settlement)
        settlements = get_player_buildings(state, color, SETTLEMENT)
        for node_id in settlements:
            if player_can_afford_city(state, color):
                actions.append(Action(color, ActionType.BUILD_CITY, node_id))

        # Build settlement
        if player_can_afford_settlement(state, color):
            actions.extend(settlement_possibilities(state, color))

        # Build road
        if player_can_afford_road(state, color):
            actions.extend(road_possibilities(state, color))

        # Buy dev card
        if player_can_afford_dev_card(state, color):
            actions.append(Action(color, ActionType.BUY_DEVELOPMENT_CARD, None))

        # Play dev cards (if played has_rolled and hasn't played one this turn)
        if player_has_rolled(state, color) and can_play_dev(state, color):
            actions.extend(dev_card_possibilities(state, color))

        # Trade
        actions.extend(maritime_trade_possibilities(state, color))
        
        # 🔥 這裡是關鍵：添加玩家間交易！
        if player_has_rolled(state, color) and not getattr(state, 'is_resolving_trade', False):
            actions.extend(domestic_trade_possibilities(state, color))

        # End turn (should be available for current player, if rolled)
        if player_has_rolled(state, color):
            actions.append(Action(color, ActionType.END_TURN, None))

        return actions
    elif action_prompt == ActionPrompt.DISCARD:
        return discard_possibilities(color)
    elif action_prompt == ActionPrompt.DECIDE_TRADE:
        # REJECT_TRADE 也應該使用 10-tuple
        trade_value = state.current_trade[:10]  # 只取前10個元素
        actions = [Action(color, ActionType.REJECT_TRADE, trade_value)]

        # can only accept if have enough cards
        freqdeck = get_player_freqdeck(state, color)
        asked = state.current_trade[5:10]
        if freqdeck_contains(freqdeck, asked):
                # ACCEPT_TRADE 應該使用 10-tuple (不包含發起玩家索引)
            trade_value = state.current_trade[:10]  # 只取前10個元素
            actions.append(Action(color, ActionType.ACCEPT_TRADE, trade_value))

        return actions
    elif action_prompt == ActionPrompt.DECIDE_ACCEPTEES:
        # you should be able to accept for each of the "accepting players"
        actions = [Action(color, ActionType.CANCEL_TRADE, None)]

        for other_color, accepted in zip(state.colors, state.acceptees):
            if accepted is True:  # 明確檢查 True
                actions.append(
                    Action(
                        color,
                        ActionType.CONFIRM_TRADE,
                        (*state.current_trade[:10], other_color),
                    )
                )
        return actions
    else:
        raise RuntimeError("Unknown ActionPrompt: " + str(action_prompt))


def monopoly_possibilities(color) -> List[Action]:
    return [Action(color, ActionType.PLAY_MONOPOLY, card) for card in RESOURCES]


def year_of_plenty_possibilities(color, freqdeck: List[int]) -> List[Action]:
    options: Set[Union[Tuple[FastResource, FastResource], Tuple[FastResource]]] = set()
    for i, first_card in enumerate(RESOURCES):
        for j in range(i, len(RESOURCES)):
            second_card = RESOURCES[j]  # doing it this way to not repeat

            to_draw = freqdeck_from_listdeck([first_card, second_card])
            if freqdeck_contains(freqdeck, to_draw):
                options.add((first_card, second_card))
            else:  # try allowing player select 1 card only.
                if freqdeck_can_draw(freqdeck, 1, first_card):
                    options.add((first_card,))
                if freqdeck_can_draw(freqdeck, 1, second_card):
                    options.add((second_card,))

    return list(
        map(
            lambda cards: Action(color, ActionType.PLAY_YEAR_OF_PLENTY, tuple(cards)),
            options,
        )
    )


def road_building_possibilities(state, color, check_money=True) -> List[Action]:
    key = player_key(state, color)

    # Check if can't build any more roads.
    has_roads_available = state.player_state[f"{key}_ROADS_AVAILABLE"] > 0
    if not has_roads_available:
        return []

    # Check if need to pay for roads but can't afford them.
    has_money = player_resource_freqdeck_contains(state, color, ROAD_COST_FREQDECK)
    if check_money and not has_money:
        return []

    buildable_edges = state.board.buildable_edges(color)
    return [Action(color, ActionType.BUILD_ROAD, edge) for edge in buildable_edges]


def settlement_possibilities(state, color, initial_build_phase=False) -> List[Action]:
    if initial_build_phase:
        buildable_node_ids = state.board.buildable_node_ids(
            color, initial_build_phase=True
        )
        return [
            Action(color, ActionType.BUILD_SETTLEMENT, node_id)
            for node_id in buildable_node_ids
        ]
    else:
        key = player_key(state, color)
        has_money = player_resource_freqdeck_contains(
            state, color, SETTLEMENT_COST_FREQDECK
        )
        has_settlements_available = (
            state.player_state[f"{key}_SETTLEMENTS_AVAILABLE"] > 0
        )
        if has_money and has_settlements_available:
            buildable_node_ids = state.board.buildable_node_ids(color)
            return [
                Action(color, ActionType.BUILD_SETTLEMENT, node_id)
                for node_id in buildable_node_ids
            ]
        else:
            return []


def city_possibilities(state, color) -> List[Action]:
    key = player_key(state, color)

    can_buy_city = player_resource_freqdeck_contains(state, color, CITY_COST_FREQDECK)
    if not can_buy_city:
        return []

    has_cities_available = state.player_state[f"{key}_CITIES_AVAILABLE"] > 0
    if not has_cities_available:
        return []

    return [
        Action(color, ActionType.BUILD_CITY, node_id)
        for node_id in get_player_buildings(state, color, SETTLEMENT)
    ]


def robber_possibilities(state, color) -> List[Action]:
    actions = []
    for coordinate, tile in state.board.map.land_tiles.items():
        if coordinate == state.board.robber_coordinate:
            continue  # ignore. must move robber.

        # each tile can yield a (move-but-cant-steal) action or
        #   several (move-and-steal-from-x) actions.
        to_steal_from = set()  # set of player_indexs
        for node_id in tile.nodes.values():
            building = state.board.buildings.get(node_id, None)
            if building is not None:
                candidate_color = building[0]
                if (
                    player_num_resource_cards(state, candidate_color) >= 1
                    and color != candidate_color  # can't play yourself
                ):
                    to_steal_from.add(candidate_color)

        if len(to_steal_from) == 0:
            actions.append(
                Action(color, ActionType.MOVE_ROBBER, (coordinate, None, None))
            )
        else:
            for enemy_color in to_steal_from:
                actions.append(
                    Action(
                        color, ActionType.MOVE_ROBBER, (coordinate, enemy_color, None)
                    )
                )

    return actions


def initial_road_possibilities(state, color) -> List[Action]:
    # Must be connected to last settlement
    last_settlement_node_id = state.buildings_by_color[color][SETTLEMENT][-1]

    buildable_edges = filter(
        lambda edge: last_settlement_node_id in edge,
        state.board.buildable_edges(color),
    )
    return [Action(color, ActionType.BUILD_ROAD, edge) for edge in buildable_edges]


def discard_possibilities(color) -> List[Action]:
    return [Action(color, ActionType.DISCARD, None)]
    # TODO: Be robust to high dimensionality of DISCARD
    # hand = player.resource_deck.to_array()
    # num_cards = player.resource_deck.num_cards()
    # num_to_discard = num_cards // 2

    # num_possibilities = ncr(num_cards, num_to_discard)
    # if num_possibilities > 100:  # if too many, just take first N
    #     return [Action(player, ActionType.DISCARD, hand[:num_to_discard])]

    # to_discard = itertools.combinations(hand, num_to_discard)
    # return list(
    #     map(
    #         lambda combination: Action(player, ActionType.DISCARD, combination),
    #         to_discard,
    #     )
    # )


def ncr(n, r):
    """n choose r. helper for discard_possibilities"""
    r = min(r, n - r)
    numer = reduce(op.mul, range(n, n - r, -1), 1)
    denom = reduce(op.mul, range(1, r + 1), 1)
    return numer // denom


def maritime_trade_possibilities(state, color) -> List[Action]:
    hand_freqdeck = [
        player_num_resource_cards(state, color, resource) for resource in RESOURCES
    ]
    port_resources = state.board.get_player_port_resources(color)
    trade_offers = inner_maritime_trade_possibilities(
        hand_freqdeck, state.resource_freqdeck, port_resources
    )

    return list(
        map(lambda t: Action(color, ActionType.MARITIME_TRADE, t), trade_offers)
    )


def inner_maritime_trade_possibilities(hand_freqdeck, bank_freqdeck, port_resources):
    """This inner function is to make this logic more shareable"""
    trade_offers = set()

    # Get lowest rate per resource
    rates: Dict[FastResource, int] = {WOOD: 4, BRICK: 4, SHEEP: 4, WHEAT: 4, ORE: 4}
    if None in port_resources:
        rates = {WOOD: 3, BRICK: 3, SHEEP: 3, WHEAT: 3, ORE: 3}
    for resource in port_resources:
        if resource != None:
            rates[resource] = 2

    # For resource in hand
    for index, resource in enumerate(RESOURCES):
        amount = hand_freqdeck[index]
        if amount >= rates[resource]:
            resource_out: List[Any] = [resource] * rates[resource]
            resource_out += [None] * (4 - rates[resource])
            for j_resource in RESOURCES:
                if (
                    resource != j_resource
                    and freqdeck_count(bank_freqdeck, j_resource) > 0
                ):
                    trade_offer = tuple(resource_out + [j_resource])
                    trade_offers.add(trade_offer)

    return trade_offers


def domestic_trade_possibilities(state, color) -> List[Action]:
    """生成玩家間交易提案"""
    actions = []
    
    # 檢查交易次數限制
    key = player_key(state, color)
    trades_offered = state.player_state.get(f"{key}_TRADES_OFFERED_THIS_TURN", 0)
    
    # 如果已經達到交易次數上限（2次），則不生成任何交易選項
    if trades_offered >= 2:
        return actions
    
    # 獲取玩家資源
    player_resources = [
        state.player_state.get(f'{key}_WOOD_IN_HAND', 0),
        state.player_state.get(f'{key}_BRICK_IN_HAND', 0), 
        state.player_state.get(f'{key}_SHEEP_IN_HAND', 0),
        state.player_state.get(f'{key}_WHEAT_IN_HAND', 0),
        state.player_state.get(f'{key}_ORE_IN_HAND', 0),
    ]
    
    total_resources = sum(player_resources)
    
    # 需要至少 1 個資源才能提出交易
    if total_resources < 1:
        return actions
    
    # 生成 1:1 交易提案
    for give_resource_idx, give_count in enumerate(player_resources):
        if give_count > 0:  # 有這種資源可以給出
            for ask_resource_idx in range(5):
                if give_resource_idx != ask_resource_idx:  # 不同資源
                    # 創建交易格式：[give_wood, give_brick, give_sheep, give_wheat, give_ore, ask_wood, ask_brick, ask_sheep, ask_wheat, ask_ore]
                    trade_offer = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                    trade_offer[give_resource_idx] = 1  # 給出 1 個資源
                    trade_offer[5 + ask_resource_idx] = 1  # 要求 1 個資源
                    
                    actions.append(Action(color, ActionType.OFFER_TRADE, tuple(trade_offer)))
    
    # 如果有多個資源，也生成 2:1 交易
    for give_resource_idx, give_count in enumerate(player_resources):
        if give_count >= 2:  # 有 2+ 個資源
            for ask_resource_idx in range(5):
                if give_resource_idx != ask_resource_idx:
                    # 2:1 交易
                    trade_offer = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                    trade_offer[give_resource_idx] = 2
                    trade_offer[5 + ask_resource_idx] = 1
                    
                    actions.append(Action(color, ActionType.OFFER_TRADE, tuple(trade_offer)))
    
    return actions


def player_can_afford_city(state, color):
    """檢查玩家是否能負擔得起城市"""
    from catanatron.models.decks import CITY_COST_FREQDECK
    return player_resource_freqdeck_contains(state, color, CITY_COST_FREQDECK)

def player_can_afford_settlement(state, color):
    """檢查玩家是否能負擔得起定居點"""
    from catanatron.models.decks import SETTLEMENT_COST_FREQDECK
    return player_resource_freqdeck_contains(state, color, SETTLEMENT_COST_FREQDECK)

def player_can_afford_road(state, color):
    """檢查玩家是否能負擔得起道路"""
    from catanatron.models.decks import ROAD_COST_FREQDECK
    return player_resource_freqdeck_contains(state, color, ROAD_COST_FREQDECK)

def can_play_dev(state, color):
    """檢查玩家是否可以玩發展卡"""
    # 檢查玩家是否可以玩任何發展卡
    from catanatron.state_functions import player_key
    key = player_key(state, color)
    
    # 檢查是否已經在本回合玩過發展卡
    if state.player_state.get(f"{key}_HAS_PLAYED_DEVELOPMENT_CARD_IN_TURN", False):
        return False
    
    # 檢查是否有任何可以玩的發展卡
    dev_cards = ["KNIGHT", "YEAR_OF_PLENTY", "MONOPOLY", "ROAD_BUILDING"]
    for dev_card in dev_cards:
        if (state.player_state.get(f"{key}_{dev_card}_IN_HAND", 0) >= 1 and
            state.player_state.get(f"{key}_{dev_card}_OWNED_AT_START", False)):
            return True
    
    return False

def road_possibilities(state, color):
    """生成道路建設可能性"""
    return road_building_possibilities(state, color)

def dev_card_possibilities(state, color):
    """生成發展卡遊玩可能性"""
    actions = []
    
    from catanatron.state_functions import player_key
    key = player_key(state, color)
    
    # 檢查是否已經在本回合玩過發展卡
    if state.player_state.get(f"{key}_HAS_PLAYED_DEVELOPMENT_CARD_IN_TURN", False):
        return actions
    
    # Knight card
    if (state.player_state.get(f"{key}_KNIGHT_IN_HAND", 0) >= 1 and
        state.player_state.get(f"{key}_KNIGHT_OWNED_AT_START", False)):
        actions.append(Action(color, ActionType.PLAY_KNIGHT_CARD, None))
    
    # Year of Plenty
    if (state.player_state.get(f"{key}_YEAR_OF_PLENTY_IN_HAND", 0) >= 1 and
        state.player_state.get(f"{key}_YEAR_OF_PLENTY_OWNED_AT_START", False)):
        actions.extend(year_of_plenty_possibilities(color, state.resource_freqdeck))
    
    # Monopoly
    if (state.player_state.get(f"{key}_MONOPOLY_IN_HAND", 0) >= 1 and
        state.player_state.get(f"{key}_MONOPOLY_OWNED_AT_START", False)):
        actions.extend(monopoly_possibilities(color))
    
    # Road Building
    if (state.player_state.get(f"{key}_ROAD_BUILDING_IN_HAND", 0) >= 1 and
        state.player_state.get(f"{key}_ROAD_BUILDING_OWNED_AT_START", False)):
        actions.append(Action(color, ActionType.PLAY_ROAD_BUILDING, None))
    
    return actions
