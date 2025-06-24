import json
import logging
import traceback
from typing import List
import requests
import asyncio
import websockets
import time

from flask import Response, Blueprint, jsonify, abort, request

from catanatron.web.models import upsert_game_state, get_game_state
from catanatron.json import GameEncoder, action_from_json
from catanatron.models.player import Color, Player, RandomPlayer
from catanatron.game import Game
from catanatron.players.value import ValueFunctionPlayer
from catanatron.players.minimax import AlphaBetaPlayer
from catanatron.players.llm import LLMPlayer
from catanatron.web.mcts_analysis import GameAnalyzer

bp = Blueprint("api", __name__, url_prefix="/api")

# WebSocket connection status tracking - simplified for port 8100 status
WEBSOCKET_PORTS = {
    8001: "RED",
    8002: "BLUE", 
    8003: "WHITE",
    8004: "ORANGE"
}

import subprocess
import socket

# 添加 WebSocket 遊戲狀態代理功能
# 在 Docker 環境中，使用服務名稱而不是 localhost
WEBSOCKET_STATUS_URL = "http://websocketllm:8100/status"
WEBSOCKET_GAME_ID = "websocket_multiplayer_game"  # 固定的遊戲 ID 用於 WebSocket 遊戲

def player_factory(player_key):
    if player_key[0] == "CATANATRON":
        return AlphaBetaPlayer(player_key[1], 2, True)
    elif player_key[0] == "RANDOM":
        return RandomPlayer(player_key[1])
    elif player_key[0] == "HUMAN":
        return ValueFunctionPlayer(player_key[1], is_bot=False)
    elif player_key[0] == "LLM":
        return LLMPlayer(player_key[1])
    else:
        raise ValueError("Invalid player key")

@bp.route("/games", methods=("POST",))
def post_game_endpoint():
    if not request.is_json or request.json is None or "players" not in request.json:
        abort(400, description="Missing or invalid JSON body: 'players' key required")
    player_keys = request.json["players"]
    print(request.json["players"])
    player_keys = [
        "CATANATRON", "CATANATRON", "RANDOM", "LLM"
    ]
    players = list(map(player_factory, zip(player_keys, Color)))

    game = Game(players=players)
    upsert_game_state(game)
    return jsonify({"game_id": game.id})


@bp.route("/games/<string:game_id>/states/<string:state_index>", methods=("GET",))
def get_game_endpoint(game_id, state_index):
    parsed_state_index = _parse_state_index(state_index)
    game = get_game_state(game_id, parsed_state_index)
    if game is None:
        abort(404, description="Resource not found")

    return Response(
        response=json.dumps(game, cls=GameEncoder),
        status=200,
        mimetype="application/json",
    )


@bp.route("/games/<string:game_id>/actions", methods=["POST"])
def post_action_endpoint(game_id):
    game = get_game_state(game_id)
    if game is None:
        abort(404, description="Resource not found")

    if game.winning_color() is not None:
        return Response(
            response=json.dumps(game, cls=GameEncoder),
            status=200,
            mimetype="application/json",
        )

    # TODO: remove `or body_is_empty` when fully implement actions in FE
    body_is_empty = (not request.data) or request.json is None or request.json == {}
    if game.state.current_player().is_bot or body_is_empty:
        game.play_tick()
        upsert_game_state(game)
    else:
        action = action_from_json(request.json)
        game.execute(action)
        upsert_game_state(game)

    return Response(
        response=json.dumps(game, cls=GameEncoder),
        status=200,
        mimetype="application/json",
    )


@bp.route("/stress-test", methods=["GET"])
def stress_test_endpoint():
    players = [
        AlphaBetaPlayer(Color.RED, 2, True),
        AlphaBetaPlayer(Color.BLUE, 2, True),
        AlphaBetaPlayer(Color.ORANGE, 2, True),
        AlphaBetaPlayer(Color.WHITE, 2, True),
    ]
    game = Game(players=players)
    game.play_tick()
    return Response(
        response=json.dumps(game, cls=GameEncoder),
        status=200,
        mimetype="application/json",
    )


@bp.route(
    "/games/<string:game_id>/states/<string:state_index>/mcts-analysis", methods=["GET"]
)
def mcts_analysis_endpoint(game_id, state_index):
    """Get MCTS analysis for specific game state."""
    logging.info(f"MCTS analysis request for game {game_id} at state {state_index}")

    # Convert 'latest' to None for consistency with get_game_state
    parsed_state_index = _parse_state_index(state_index)
    try:
        game = get_game_state(game_id, parsed_state_index)
        if game is None:
            logging.error(
                f"Game/state not found: {game_id}/{state_index}"
            )  # Use original state_index for logging
            abort(404, description="Game state not found")

        analyzer = GameAnalyzer(num_simulations=100)
        probabilities = analyzer.analyze_win_probabilities(game)

        logging.info(f"Analysis successful. Probabilities: {probabilities}")
        return Response(
            response=json.dumps(
                {
                    "success": True,
                    "probabilities": probabilities,
                    "state_index": (
                        parsed_state_index
                        if parsed_state_index is not None
                        else len(game.state.actions)
                    ),
                }
            ),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Error in MCTS analysis endpoint: {str(e)}")
        logging.error(traceback.format_exc())
        return Response(
            response=json.dumps(
                {"success": False, "error": str(e), "trace": traceback.format_exc()}
            ),
            status=500,
            mimetype="application/json",
        )


def _parse_state_index(state_index_str: str):
    """Helper function to parse and validate state_index."""
    if state_index_str == "latest":
        return None
    try:
        return int(state_index_str)
    except ValueError:
        abort(
            400,
            description="Invalid state_index format. state_index must be an integer or 'latest'.",
        )


# ===== Debugging Routes
# @app.route(
#     "/games/<string:game_id>/players/<int:player_index>/features", methods=["GET"]
# )
# def get_game_feature_vector(game_id, player_index):
#     game = get_game_state(game_id)
#     if game is None:
#         abort(404, description="Resource not found")

#     return create_sample(game, game.state.colors[player_index])


# @app.route("/games/<string:game_id>/value-function", methods=["GET"])
# def get_game_value_function(game_id):
#     game = get_game_state(game_id)
#     if game is None:
#         abort(404, description="Resource not found")

#     # model = tf.keras.models.load_model("data/models/mcts-rep-a")
#     model2 = tf.keras.models.load_model("data/models/mcts-rep-b")
#     feature_ordering = get_feature_ordering()
#     indices = [feature_ordering.index(f) for f in NUMERIC_FEATURES]
#     data = {}
#     for color in game.state.colors:
#         sample = create_sample_vector(game, color)
#         # scores = model.call(tf.convert_to_tensor([sample]))

#         inputs1 = [create_board_tensor(game, color)]
#         inputs2 = [[float(sample[i]) for i in indices]]
#         scores2 = model2.call(
#             [tf.convert_to_tensor(inputs1), tf.convert_to_tensor(inputs2)]
#         )
#         data[color.value] = float(scores2.numpy()[0][0])

#     return data

def get_websocket_game_status():
    """取得 WebSocket 遊戲引擎的狀態"""
    try:
        response = requests.get(WEBSOCKET_STATUS_URL, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException as e:
        logging.warning(f"Failed to connect to WebSocket game engine: {e}")
        return None

def convert_websocket_status_to_game_format(ws_status):
    """將 WebSocket 狀態轉換為 Flask API 遊戲格式"""
    if not ws_status or not ws_status.get("game_status", {}).get("game_started"):
        return None
        
    try:
        game_state = ws_status.get("game_status", {}).get("game_state", {})
        
        # 構建基本的遊戲狀態資訊
        game_info = {
            "game_id": WEBSOCKET_GAME_ID,
            "status": "active" if not game_state.get("game_finished") else "finished",
            "current_player": game_state.get("current_player"),
            "turn_number": game_state.get("turn_number", 0),
            "winner": game_state.get("winner"),
            "connected_players": ws_status.get("game_status", {}).get("connected_players", 0),
            "player_connections": ws_status.get("player_connections", {}),
            "summary": ws_status.get("summary", "Unknown status"),
            "websocket_engine_info": {
                "min_players": ws_status.get("websocket_game_engine", {}).get("min_players"),
                "max_players": ws_status.get("websocket_game_engine", {}).get("max_players"),
                "waiting_time": ws_status.get("websocket_game_engine", {}).get("waiting_time")
            }
        }
        
        return game_info
    except Exception as e:
        logging.error(f"Error converting WebSocket status: {e}")
        return None

@bp.route("/websocket-games/current", methods=["GET"])
def get_current_websocket_game():
    """取得目前的 WebSocket 多人遊戲狀態"""
    ws_status = get_websocket_game_status()
    
    if ws_status is None:
        return jsonify({
            "error": "WebSocket game engine not available",
            "message": "Cannot connect to WebSocket game engine on port 8100"
        }), 503
    
    game_info = convert_websocket_status_to_game_format(ws_status)
    
    if game_info is None:
        return jsonify({
            "status": "no_active_game",
            "message": "No active WebSocket game",
            "websocket_status": ws_status
        })
    
    return jsonify(game_info)

@bp.route("/websocket-games/current/detailed", methods=["GET"])
def get_current_websocket_game_detailed():
    """取得目前 WebSocket 多人遊戲的詳細狀態（原始格式）"""
    ws_status = get_websocket_game_status()
    
    if ws_status is None:
        return jsonify({
            "error": "WebSocket game engine not available",
            "message": "Cannot connect to WebSocket game engine on port 8100"
        }), 503
    
    return jsonify(ws_status)

@bp.route("/games/websocket/<string:game_id>/states/latest", methods=["GET"])
def get_websocket_game_state(game_id):
    """讓前端可以用一般的遊戲 API 格式訪問 WebSocket 遊戲狀態"""
    if game_id != WEBSOCKET_GAME_ID:
        abort(404, description="WebSocket game not found")
    
    ws_status = get_websocket_game_status()
    
    if ws_status is None:
        abort(503, description="WebSocket game engine not available")
    
    # 檢查遊戲是否已開始
    if not ws_status.get("game_status", {}).get("game_started"):
        return jsonify({
            "error": "No active WebSocket game",
            "message": "WebSocket game has not started yet",
            "websocket_status": ws_status
        }), 404
    
    # 嘗試從資料庫取得完整的遊戲狀態
    try:
        game = get_game_state(WEBSOCKET_GAME_ID)
        if game:
            # 返回完整的遊戲狀態（與一般 Flask API 相同格式）
            return Response(
                response=json.dumps(game, cls=GameEncoder),
                status=200,
                mimetype="application/json",
            )
    except Exception as e:
        logging.warning(f"Could not get WebSocket game from database: {e}")
    
    # 如果資料庫中沒有資料，返回基本狀態資訊
    game_info = convert_websocket_status_to_game_format(ws_status)
    
    if game_info is None:
        abort(404, description="No active WebSocket game")
    
    # 返回符合前端期望的格式，但標明資料不完整
    return jsonify({
        "game_id": game_id,
        "type": "websocket_multiplayer", 
        "state": game_info,
        "last_updated": time.time(),
        "warning": "Full game state not available - only connection status",
        "recommendation": "Use WebSocket connection for real-time game data"
    })

@bp.route("/games/websocket/<string:game_id>/states/<string:state_index>", methods=["GET"])
def get_websocket_game_state_by_index(game_id, state_index):
    """取得 WebSocket 遊戲的特定狀態"""
    if game_id != WEBSOCKET_GAME_ID:
        abort(404, description="WebSocket game not found")
    
    # 只支援從資料庫取得歷史狀態
    try:
        parsed_state_index = _parse_state_index(state_index)
        game = get_game_state(WEBSOCKET_GAME_ID, parsed_state_index)
        
        return Response(
            response=json.dumps(game, cls=GameEncoder),
            status=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"Error getting WebSocket game state: {e}")
        abort(404, description="WebSocket game state not found in database")

@bp.route("/games/websocket/<string:game_id>/full-state", methods=["GET"])
def get_websocket_game_full_state(game_id):
    """取得 WebSocket 遊戲的完整即時狀態（需要 WebSocket 引擎支援）"""
    if game_id != WEBSOCKET_GAME_ID:
        abort(404, description="WebSocket game not found")
    
    # 嘗試直接從 WebSocket 引擎取得完整遊戲狀態
    try:
        # 這需要 WebSocket 引擎提供新的端點
        full_state_url = WEBSOCKET_STATUS_URL.replace('/status', '/game-state')
        response = requests.get(full_state_url, timeout=5)
        
        if response.status_code == 200:
            game_data = response.json()
            return jsonify({
                "game_id": game_id,
                "type": "websocket_multiplayer_full",
                "full_game_state": game_data,
                "last_updated": time.time(),
                "source": "websocket_engine_direct"
            })
        else:
            # 回退到資料庫
            game = get_game_state(WEBSOCKET_GAME_ID)
            return Response(
                response=json.dumps(game, cls=GameEncoder),
                status=200,
                mimetype="application/json",
            )
    except Exception as e:
        logging.warning(f"Could not get full state from WebSocket engine: {e}")
        # 回退到資料庫
        try:
            game = get_game_state(WEBSOCKET_GAME_ID)
            return Response(
                response=json.dumps(game, cls=GameEncoder),
                status=200,
                mimetype="application/json",
            )
        except Exception as db_error:
            abort(503, description="Cannot get WebSocket game state from any source")

@bp.route("/games/list", methods=["GET"])
def list_all_games():
    """列出所有遊戲（包括 Flask 遊戲和 WebSocket 遊戲）"""
    games = []
    
    # 取得 Flask 遊戲（從資料庫）
    try:
        from catanatron.web.models import database_session, GameState
        with database_session() as session:
            flask_games = session.query(GameState.uuid).distinct().all()
            for (game_uuid,) in flask_games:
                games.append({
                    "game_id": game_uuid,
                    "type": "flask_single_player",
                    "source": "database"
                })
    except Exception as e:
        logging.error(f"Error fetching Flask games: {e}")
    
    # 取得 WebSocket 遊戲
    ws_status = get_websocket_game_status()
    if ws_status and ws_status.get("game_status", {}).get("game_started"):
        games.append({
            "game_id": WEBSOCKET_GAME_ID,
            "type": "websocket_multiplayer", 
            "source": "websocket_engine",
            "status": convert_websocket_status_to_game_format(ws_status)
        })
    
    return jsonify({
        "games": games,
        "total_count": len(games)
    })
