import abc
from logging import getLogger
import typing
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)


class BaseTool(abc.ABC):
    def __init__(self, master: "V1Agent"):
        super().__init__()
        self.master = master
    
    @abc.abstractmethod
    def process_tool_call(self, tool_call: ChatCompletionMessageToolCall):
        pass

    @abc.abstractmethod
    def on_new_turn(self):
        pass

    @abc.abstractmethod
    def get_tool_description(self):
        return []
