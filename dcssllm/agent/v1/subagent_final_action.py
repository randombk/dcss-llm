import typing
from typing import Dict, Optional, Any, List
from logging import getLogger

from openai import AsyncOpenAI
from dcssllm.agent.util import *
from dcssllm.agent.v1.general_instructions import *
from dcssllm.llmutils import LLMConfig

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)

class SubagentFinalAction:
    def __init__(self, master: "V1Agent", llm: LLMConfig):
        self.master = master
        self.llm = llm
        self.client = AsyncOpenAI(base_url=llm.uri, api_key=llm.secret or 'NONE')
        self.tool_config = [
            *self.master.tool_send_key_press.get_tool_description(),
        ]


    async def ai_turn(self, what_happened_last_turn: str, current_objective: str,
                      advisors: List[Dict[str, Any]]) -> Optional[Any]:
        completion = await self.client.chat.completions.create(
            model=self.llm.model,
            messages=prep_message(__name__, notnull([
                {
                    "role": "system",
                    "content": GENERAL_AGENT_INTRO,
                },
                {
                    "role": "user",
                    "content": GAME_UI_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": CHARACTER_PLAYSTYLE_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": KEY_BINDING_INSTRUCTIONS,
                },
                self.master.tool_longterm_memory.get_memory_message(),
                self.master.tool_shortterm_memory.get_memory_message(),
                {
                    "role": "user",
                    "content": "The current screen is:\n\n\n\n" + self.master.latest_text_only_screen + "\n\n\n\n",
                },
                {
                    "role": "user",
                    "content": f"Your current objective is: {current_objective}",
                },
                {
                    "role": "user",
                    "content": f"Last turn, you: {what_happened_last_turn}",
                },
                self.master.get_message_no_action(),
                {
                    "role": "user",
                    "content": "You have a set of advisors that can help you make decisions. They are currently saying:",
                },

                *[
                    {
                        "role": "user",
                        "content": f"{advisor['name']}: {advisor['message']}",
                    }
                    for advisor in advisors
                ],
                {
                    "role": "user",
                    "content": trim_indent("""
                        Your job is to decide what action to take next. Look at the screen and the information provided by
                        your advisors, and decide what action you should take next. Send a key press to the game to make
                        progress on your current objective.

                        Remember that you are located at the '@' symbol, and that '#' represent walls. Avoid constantly
                        trying to walk into walls.

                        Use the map to figure out where you are and where you can go. Use the information on the screen
                        as well as your previous responses and though processes to make decisions.

                        Refer to the instructions to help you understand what you can do in the game and what the symbols mean.
                    """)
                },
            ])),
            # reasoning_effort='low',
            tools=self.tool_config,
            tool_choice='required',
        )
        response = completion.choices[0].message
        if response.refusal:
            logger.info("Refusal:", response.refusal)
        if response.content:
            logger.info(response.content)
        self.master.run_tools(response.tool_calls)
