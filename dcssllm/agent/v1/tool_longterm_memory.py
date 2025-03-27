from logging import getLogger
from typing import Dict, Optional, TYPE_CHECKING

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field

from dcssllm.agent.util import trim_indent
from dcssllm.agent.v1.tool import StatefulTool

if TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)


class LongTermMemory:
    data: Dict[str, str] = {}


class ToolWriteLongTermMemoryInput(BaseModel):
    key: str = Field(description="Memory Key. Should be a unique alphanumeric string with underscores.")
    value: str = Field(description="Memory Value. Remember to quote things correctly. Avoid storing multiline strings. Write a blank value to clear the memory.")


class ToolWriteLongTermMemory(StatefulTool):
    name: str = "save_long_term_memory"
    description: str = trim_indent("""
        Writes a value to your long term memory, which will be available in future turns until you choose to
        forget it. This is a Key-Value store.
    """)
    args_schema: Optional[ArgsSchema] = ToolWriteLongTermMemoryInput

    def __init__(self, master: "V1Agent", memory: LongTermMemory):
        super().__init__(master)
        self._memory = memory
    
    def on_new_turn(self) -> None:
        pass

    def _run(
        self, key: str, value: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        logger.info(f"Writing Long-Term Memory {key} => {value}")

        if value != '':
            self._memory.data[key] = value
            return f"Successfully saved memory: {key} => {value}"
        else:
            self._memory.data.pop(key, None)
            return f"Successfully cleared memory for key: {key}"
