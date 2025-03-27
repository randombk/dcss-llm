from logging import getLogger
from typing import Optional, TYPE_CHECKING, List

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools.base import ArgsSchema
from langchain_core.messages import HumanMessage
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
    name: str = "get_game_state_change_since_last_turn"
    description: str = "Gets a summary of the changes in the game state since the last turn."
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

    def create_message(self) -> List[HumanMessage]:
        if self._current_state:
            return [
                HumanMessage(f"Here is the current state of the game:\n\n{self._current_state.get_summary_without_map()}"),
                HumanMessage(f"Here is your memory of the game map:\n\n{self._current_state.get_map()}"),
                HumanMessage(self._current_state.get_nearby_enemy_summary()),
            ]
        else:
            return []
