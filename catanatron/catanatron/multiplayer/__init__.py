"""
Multiplayer game components for Catanatron
"""

__all__ = ['GameEngineServer', 'LLMAgentClient']

def __getattr__(name):
    """Lazy import to avoid RuntimeWarning when running modules as scripts"""
    if name == 'GameEngineServer':
        from .game_engine_server import GameEngineServer
        return GameEngineServer
    elif name == 'LLMAgentClient':
        from .llm_agent_client import LLMAgentClient
        return LLMAgentClient
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 
