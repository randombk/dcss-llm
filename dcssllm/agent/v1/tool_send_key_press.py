import json
from logging import getLogger
import typing
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

from dcssllm.agent.v1.tool import BaseTool
from dcssllm.curses_utils import CursesApplication
from dcssllm.keycodes import Keycode

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)

class ToolSendKeyPress(BaseTool):
    def __init__(self, master: "V1Agent", game: CursesApplication):
        super().__init__(master)
        self.game = game
        self.sent_key = False
        self.previous_key = ''
    
    def process_tool_call(self, tool_call: ChatCompletionMessageToolCall):
        if tool_call.function.name == "send_key_press" and self.sent_key is False:
            self.sent_key = True

            arguments = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
            action = arguments["keycode"]
            self.previous_key = action
            self.sent_key = True

            logger.info(f"Sending key press: {action}")

            if action.upper() == "UP":
                self.game.send_keycode(Keycode.UP)
            elif action.upper() == "DOWN":
                self.game.send_keycode(Keycode.DOWN)
            elif action.upper() == "LEFT":
                self.game.send_keycode(Keycode.LEFT)
            elif action.upper() == "RIGHT":
                self.game.send_keycode(Keycode.RIGHT)
            elif action.upper() == "ENTER":
                self.game.send_keycode(Keycode.ENTER)
            elif action.upper() == "ESCAPE":
                self.game.send_keycode(Keycode.ESC)
            elif action.upper() == "BACKSPACE":
                self.game.send_keycode(Keycode.BACKSPACE)
            elif action.upper() == "SPACE":
                self.game.send_keycode(Keycode.SPACE)
            elif action.upper() == "TAB":
                self.game.send_keycode(Keycode.TAB)
            elif len(action) == 1:
                self.game.send_key(action)

    def on_new_turn(self):
        self.sent_key = False

    def get_tool_description(self):
        return [{
            "type": "function",
            "function": {
                "name": "send_key_press",
                "description": "Sends a key press to the game. You may only send a single key press per function call.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keycode": {
                            "type": "string",
                            "description": "A single case-sensitive character, or one of 'ENTER', 'ESCAPE', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'BACKSPACE', 'TAB'",
                        }
                    },
                    "action": [ "location" ],
                    "additionalProperties": False
                },
                "strict": True
            }
        }]
