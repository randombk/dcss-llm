from logging import getLogger
from typing import *

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field

from dcssllm.agent.v1.tool import StatefulTool
from dcssllm.curses_utils import CursesApplication
from dcssllm.keycodes import Keycode

if TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)


class Input(BaseModel):
    keycode: str = Field(description="A single case-sensitive character, or one of 'ENTER', 'ESCAPE', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'BACKSPACE', 'TAB'")


class ToolSendKeyPress(StatefulTool):
    name: str = "send_key_press"
    description: str = "Sends a key press to the game and end your turn. You may only send a single key press per function call."
    args_schema: Optional[ArgsSchema] = Input
    return_direct: bool = True

    def __init__(self, master: "V1Agent", game: CursesApplication):
        super().__init__(master)

        self._game = game
        self._sent_key = False
        self._previous_key = ''
    
    def on_new_turn(self):
        self._sent_key = False

    def _run(
        self, keycode: str, 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        if not self._sent_key:
            self._sent_key = True
            self._previous_key = keycode
            logger.info(f"Sending key press: {keycode}")

            if keycode.upper() == "UP":
                self._game.send_keycode(Keycode.UP)
            elif keycode.upper() == "DOWN":
                self._game.send_keycode(Keycode.DOWN)
            elif keycode.upper() == "LEFT":
                self._game.send_keycode(Keycode.LEFT)
            elif keycode.upper() == "RIGHT":
                self._game.send_keycode(Keycode.RIGHT)
            elif keycode.upper() == "ENTER":
                self._game.send_keycode(Keycode.ENTER)
            elif keycode.upper() == "ESCAPE":
                self._game.send_keycode(Keycode.ESC)
            elif keycode.upper() == "BACKSPACE":
                self._game.send_keycode(Keycode.BACKSPACE)
            elif keycode.upper() == "SPACE":
                self._game.send_keycode(Keycode.SPACE)
            elif keycode.upper() == "TAB":
                self._game.send_keycode(Keycode.TAB)
            elif len(keycode) == 1:
                self._game.send_key(keycode)
