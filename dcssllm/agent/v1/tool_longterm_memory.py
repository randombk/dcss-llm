import json
from logging import getLogger
import typing
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

from dcssllm.agent.util import trim_indent
from dcssllm.agent.v1.tool import BaseTool

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)

class ToolLongTermMemory(BaseTool):
    def __init__(self, master: "V1Agent"):
        super().__init__(master)
        self.memory = {}
    
    def process_tool_call(self, tool_call: ChatCompletionMessageToolCall):
        if tool_call.function.name == "save_long_term_memory":
            arguments = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
            key = arguments["key"]
            value = arguments["value"]

            logger.info(f"Writing Long-Term Memory {key} => {value}")

            if value != '':
                self.memory[key] = value
            else:
                self.memory.pop(key, None)

    def on_new_turn(self):
        pass

    def get_tool_description(self):
        return [{
            "type": "function",
            "function": {
                "name": "save_long_term_memory",
                "description": trim_indent("""
                    Writes a value to your long term memory, which will be available in future turns until you choose to
                    forget it. This is a Key-Value store.
                """),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Memory Key. Should be a unique alphanumeric string with underscores.",
                        },
                        "value": {
                            "type": "string",
                            "description": "Memory Value. Remember to quote things correctly. Avoid storing multiline strings.",
                        }
                    },
                    "action": [ "location" ],
                    "additionalProperties": False
                },
                "strict": True
            }
        }]
    
    def get_memory_dump(self) -> str:
        return json.dumps(self.memory, indent=4)
    
    def get_memory_message(self):
        if len(self.memory) == 0:
            return None

        return {
            "role": "user",
            "content": "You previously remembered the following facts in your long-term memory:\n\n" + 
                '\n'.join([f"    {key} => {value}" for key, value in self.memory.items()])
        },
