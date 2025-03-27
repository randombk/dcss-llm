import abc
from logging import getLogger
from typing import *
from langchain_core.tools import BaseTool

if TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)


class StatefulTool(BaseTool):
    """
    A tool that contains stateful information about the play session.
    """
    # master: Any

    def __init__(self, master: "V1Agent"):
        super().__init__()
        self._master = master

    @abc.abstractmethod
    def on_new_turn(self):
        pass

