import json
from logging import getLogger
from typing import Dict, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools.base import ArgsSchema
from langchain_core.messages import SystemMessage, HumanMessage

from dcssllm.agent.util import trim_indent
from dcssllm.agent.v1.tool import StatefulTool

if TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)


class LongTermMemory:
    data: Dict[str, str] = {}

    def create_message(self) -> HumanMessage:
        if self.data:
            memories = "\n".join([f"{k}: {v}" for k, v in self.data.items()])
            return HumanMessage(f"Here are your long term memories:\n\n{memories}")
        else:
            return HumanMessage("You don't have any long-term memories yet.")


class ToolWriteLongTermMemoryInput(BaseModel):
    key: str = Field(description="Memory Key. Should be a unique alphanumeric string with underscores.")
    value: str = Field(description="Memory Value. Remember to quote things correctly. Avoid storing multiline strings. Write a blank value to clear the memory.")


class ToolWriteLongTermMemory(StatefulTool):
    name: str = "save_long_term_memory"
    description: str = trim_indent("""
        Writes a value to your long term memory, which will be available in future turns until you choose to
        forget it. Use this to remember important things that you want to remember for a long time, like the
        locations of important items or monsters. You can also use it to remember your own past actions and
        decisions, so you can learn from them.

        Do not use this to remember things that are not important, or that you can easily look up.
        For example, you don't need to remember your current health, as that is displayed in the UI.

        This is a Key-Value store.
    """)
    args_schema: Optional[ArgsSchema] = ToolWriteLongTermMemoryInput

    def __init__(self, master: "V1Agent", memory: LongTermMemory):
        super().__init__(master)
        self._memory = memory
        self._read_from_file()
    def on_new_turn(self) -> None:
        pass

    def _run(
        self, key: str, value: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        logger.info(f"Writing Long-Term Memory {key} => {value}")

        if value != '':
            self._memory.data[key] = value
            self._write_to_file()
            return f"Successfully saved memory: {key} => {value}"
        else:
            self._memory.data.pop(key, None)
            self._write_to_file()
            return f"Successfully cleared memory for key: {key}"

    def _write_to_file(self) -> None:
        # Dump the memory to a file
        with open('tmp/longterm_memory.json', 'w') as f:
            json.dump(self._memory.data, f)

    def _read_from_file(self) -> None:
        try:
            with open('tmp/longterm_memory.json', 'r') as f:
                self._memory.data = json.load(f)
        except FileNotFoundError:
            logger.warning("No long-term memory file found")
