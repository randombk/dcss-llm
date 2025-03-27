from logging import getLogger
from typing import Optional, TYPE_CHECKING

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field

from dcssllm.agent.v1.game_state import GameState
from dcssllm.agent.v1.tool import StatefulTool

if TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)


class Input(BaseModel):
    """No args needed for this tool"""
    pass


class ToolGameState(StatefulTool):
    name: str = "get_game_state"
    description: str = "Gets the current state of the game and any changes since the last turn."
    args_schema: Optional[ArgsSchema] = Input

    def __init__(self, master: "V1Agent"):
        super().__init__(master)
        self._prev_state: Optional[GameState] = None
        self._current_state: Optional[GameState] = None

    def on_new_turn(self) -> None:
        self._prev_state = self._current_state
        self._current_state = GameState()

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        if not self._prev_state or not self._current_state:
            return "No game state available yet."
        
        delta_summary = self._current_state.get_delta_summary(self._prev_state)
        if not delta_summary:
            return "No changes in game state since last turn."
            
        return "These things changed in the game state:\n\n" + delta_summary
