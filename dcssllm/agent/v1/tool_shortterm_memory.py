from logging import getLogger
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field

from dcssllm.agent.util import trim_indent
from dcssllm.agent.v1.tool import StatefulTool

if TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)


class ShortTermMemory:
    data: Dict[str, Tuple[str, int]] = {}


class ToolWriteShortTermMemoryInput(BaseModel):
    key: str = Field(description="Memory Key. Should be a unique alphanumeric string with underscores.")
    value: str = Field(description="Memory Value. Remember to quote things correctly. Avoid storing multiline strings.")


class ToolWriteShortTermMemory(StatefulTool):
    name: str = "save_short_term_memory"
    description: str = trim_indent("""
        Writes a value to your short term memory, which will be available in future turns. Unlike long term memory,
        short term memories will automatically be removed after a while. Use this to remember things
        that you might need to recall in the near future, but don't want to remember forever.
        
        This is a Key-Value store.
    """)
    args_schema: Optional[ArgsSchema] = ToolWriteShortTermMemoryInput

    def __init__(self, master: "V1Agent", memory: ShortTermMemory):
        super().__init__(master)
        self._memory = memory
    
    def on_new_turn(self) -> None:
        for key, value in list(self._memory.data.items()):
            if value[1] < self._master.iterations:
                self._memory.data.pop(key)

    def _run(
        self, key: str, value: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        logger.info(f"Writing Short-Term Memory {key} => {value}")

        if value != '':
            self._memory[key] = (value, self._master.iterations + 10)
            return f"Successfully saved memory: {key} => {value}"
        else:
            self._memory.pop(key, None)
            return f"Successfully cleared memory for key: {key}"
        

# class ToolReadShortTermMemoryInput(BaseModel):
#     """No args needed for this tool"""
#     pass

# class ToolReadShortTermMemory(StatefulTool):
#     name: str = "read_short_term_memory"
#     description: str = trim_indent("""
#         Reads all the values in your short term memory.
#     """)
#     args_schema: Optional[ArgsSchema] = ToolReadShortTermMemoryInput

#     def __init__(self, master: "V1Agent", memory: ShortTermMemory):
#         super().__init__(master)
#         self._memory = memory
        
#     def _run(
#         self,
#         run_manager: Optional[CallbackManagerForToolRun] = None
#     ) -> str:
#         return "You previously remembered the following facts in your short-term memory:\n\n" + \
#             '\n'.join([f"    {key} => {value[0]}" for key, value in self._memory.data.items()])
    