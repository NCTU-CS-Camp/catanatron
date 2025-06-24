"""
Classes to encode/decode catanatron classes to JSON format.
"""

import json
from enum import Enum

from catanatron.models.map import Water, Port, LandTile
from catanatron.game import Game
from catanatron.models.player import Color
from catanatron.models.enums import RESOURCES, Action, ActionType
from catanatron.state_functions import get_longest_road_length


def longest_roads_by_player(state):
    result = dict()
    for color in state.colors:
        result[color.value] = get_longest_road_length(state, color)
    return result


def action_from_json(action_json):
    """从JSON重建Action对象"""
    from catanatron.models.actions import ActionType
    from catanatron.models.player import Color
    from catanatron.models.actions import Action
    
    try:
        if isinstance(action_json, list) and len(action_json) >= 3:
            color_str, action_type_str, value = action_json[:3]
            
            # 转换颜色
            color = Color[color_str] if isinstance(color_str, str) else color_str
            
            # 转换行动类型  
            action_type = ActionType[action_type_str] if isinstance(action_type_str, str) else action_type_str
            
            # 修复：将列表转换为元组
            if isinstance(value, list):
                if action_type == ActionType.MOVE_ROBBER and len(value) >= 2:
                    # MOVE_ROBBER 特殊处理: (coordinate, victim, extra)
                    coord = tuple(value[0]) if isinstance(value[0], list) else value[0]
                    victim = Color[value[1]] if isinstance(value[1], str) and value[1] in ['RED', 'BLUE', 'WHITE', 'ORANGE'] else value[1]
                    third = value[2] if len(value) > 2 else None
                    value = (coord, victim, third)
                elif action_type == ActionType.CONFIRM_TRADE and len(value) >= 11:
                    # CONFIRM_TRADE 特殊处理：最后一个元素应该是 Color 对象
                    processed_value = []
                    for i, item in enumerate(value):
                        if i == 10:  # 最后一个元素是接受者的颜色
                            if isinstance(item, str) and item in ['RED', 'BLUE', 'WHITE', 'ORANGE']:
                                processed_value.append(Color[item])
                            else:
                                processed_value.append(item)
                        else:
                            processed_value.append(item)
                    value = tuple(processed_value)
                else:
                    # 其他行动类型统一转换为元组
                    value = tuple(value)
            
            return Action(color, action_type, value)
            
        else:
            raise ValueError(f"Invalid action_json format: {action_json}")
            
    except Exception as e:
        print(f"Error in action_from_json: {e}")
        print(f"   Input: {action_json}")
        raise


class GameEncoder(json.JSONEncoder):
    def default(self, obj):
        if obj is None:
            return None
        if isinstance(obj, str):
            return obj
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, tuple):
            return obj
        if isinstance(obj, Game):
            nodes = {}
            edges = {}
            for coordinate, tile in obj.state.board.map.tiles.items():
                for direction, node_id in tile.nodes.items():
                    building = obj.state.board.buildings.get(node_id, None)
                    color = None if building is None else building[0]
                    building_type = None if building is None else building[1]
                    nodes[node_id] = {
                        "id": node_id,
                        "tile_coordinate": coordinate,
                        "direction": self.default(direction),
                        "building": self.default(building_type),
                        "color": self.default(color),
                    }
                for direction, edge in tile.edges.items():
                    color = obj.state.board.roads.get(edge, None)
                    edge_id = tuple(sorted(edge))
                    edges[edge_id] = {
                        "id": edge_id,
                        "tile_coordinate": coordinate,
                        "direction": self.default(direction),
                        "color": self.default(color),
                    }
            return {
                "tiles": [
                    {"coordinate": coordinate, "tile": self.default(tile)}
                    for coordinate, tile in obj.state.board.map.tiles.items()
                ],
                "adjacent_tiles": obj.state.board.map.adjacent_tiles,
                "nodes": nodes,
                "edges": list(edges.values()),
                "actions": [self.default(a) for a in obj.state.actions],
                "player_state": obj.state.player_state,
                "colors": obj.state.colors,
                "bot_colors": list(
                    map(
                        lambda p: p.color, filter(lambda p: p.is_bot, obj.state.players)
                    )
                ),
                "is_initial_build_phase": obj.state.is_initial_build_phase,
                "robber_coordinate": obj.state.board.robber_coordinate,
                "current_color": obj.state.current_color(),
                "current_prompt": obj.state.current_prompt,
                "current_playable_actions": obj.state.playable_actions,
                "longest_roads_by_player": longest_roads_by_player(obj.state),
                "winning_color": obj.winning_color(),
            }
        if isinstance(obj, Water):
            return {"type": "WATER"}
        if isinstance(obj, Port):
            return {
                "id": obj.id,
                "type": "PORT",
                "direction": self.default(obj.direction),
                "resource": self.default(obj.resource),
            }
        if isinstance(obj, LandTile):
            if obj.resource is None:
                return {"id": obj.id, "type": "DESERT"}
            return {
                "id": obj.id,
                "type": "RESOURCE_TILE",
                "resource": self.default(obj.resource),
                "number": obj.number,
            }
        return json.JSONEncoder.default(self, obj)
