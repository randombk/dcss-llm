import json
from logging import getLogger
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools.base import ArgsSchema
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from dcssllm.agent.util import trim_indent
from dcssllm.agent.v1.tool import StatefulTool

if TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)


class ShortTermMemory:
    data: Dict[str, Tuple[str, int]] = {}

    def create_message(self) -> HumanMessage:
        if self.data:
            memories = "\n".join([f"{k}: {v[0]}" for k, v in self.data.items()])
            return HumanMessage(f"Here are your short term memories:\n\n{memories}")
        else:
            return HumanMessage("You don't have any short term memories yet.")


class ToolWriteShortTermMemoryInput(BaseModel):
    key: str = Field(description="Memory Key. Should be a unique alphanumeric string with underscores.")
    value: str = Field(description="Memory Value. Remember to quote things correctly. Avoid storing multiline strings.")


class ToolWriteShortTermMemory(StatefulTool):
    name: str = "save_short_term_memory"
    description: str = trim_indent("""
        Writes a value to your short term memory, which will be available in future turns. Unlike long term memory,
        short term memories will automatically be removed after a while. Use this to remember things
        that you might need to recall in the near future, but don't want to remember forever. For example, you can use
        this to remember your current objective and what you need to do to achieve it.
        
        This is a Key-Value store.
    """)
    args_schema: Optional[ArgsSchema] = ToolWriteShortTermMemoryInput

    def __init__(self, master: "V1Agent", memory: ShortTermMemory):
        super().__init__(master)
        self._memory = memory
        self._read_from_file()
        
    def on_new_turn(self) -> None:
        needs_write = False
        for key, value in list(self._memory.data.items()):
            if value[1] < self._master.iterations:
                self._memory.data.pop(key)
                needs_write = True

        if needs_write:
            self._write_to_file()

    def _run(
        self, key: str, value: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        logger.info(f"Writing Short-Term Memory {key} => {value}")

        if value != '':
            self._memory.data[key] = (value, self._master.iterations + 10)
            self._write_to_file()
            return f"Successfully saved memory: {key} => {value}"
        else:
            self._memory.data.pop(key, None)
            self._write_to_file()
            return f"Successfully cleared memory for key: {key}"
        
    def _write_to_file(self) -> None:
        # Dump the memory to a file
        with open('tmp/shortterm_memory.json', 'w') as f:
            json.dump(self._memory.data, f)
    
    def _read_from_file(self) -> None:
        try:
            with open('tmp/shortterm_memory.json', 'r') as f:
                self._memory.data = json.load(f)
        except FileNotFoundError:
            logger.warning("No short-term memory file found")

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
    