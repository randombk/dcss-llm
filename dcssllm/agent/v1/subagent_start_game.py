import typing
from logging import getLogger

from openai import AsyncOpenAI
from dcssllm.agent.util import *
from dcssllm.agent.v1.general_instructions import *
from dcssllm.llmutils import LLMConfig

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)

class SubagentStartGame:
    """
    In charge of starting a new game or resuming an existing one.
    """
    def __init__(self, master: "V1Agent", llm: LLMConfig):
        self.master = master
        self.llm = llm
        self.client = AsyncOpenAI(base_url=llm.uri, api_key=llm.secret or 'NONE')
        self.tool_config = [
            *self.master.tool_send_key_press.get_tool_description(),
        ]


    async def ai_turn(self):
        completion = await self.client.chat.completions.create(
            model=self.llm.model,
            messages=prep_message(__name__, notnull([
                {
                    "role": "system",
                    "content": GENERAL_AGENT_INTRO,
                },
                {
                    "role": "user",
                    "content": "The current screen is:\n\n" + self.master.latest_screen,
                },
                self.master.get_message_no_action(),
                {
                    "role": "user",
                    "content": trim_indent(f"""
                        Use the arrow keys to select a menu entry. Use the 'ENTER' key to confirm your selection.
                        If there's a letter next to a menu entry, you can press that letter to select it.
                    """),
                } if self.master.nothing_happened else None,
                {
                    "role": "user",
                    "content": trim_indent("""
                        Current Objective: Start a new game, or resume an existing one. Navigate the UI by interpreting
                        the screen and sending the appropriate commands to the game.

                        Choose the Minotaur Berserker class. Choose an axe as your starting weapon.

                        IMPORTANT: Prefer to resume an existing game if there is one.
                        
                        YOU SHOULD ONLY OUTPUT A SINGLE KEY PRESS TO THE GAME VIA THE TOOL CALL.
                    """)
                }
            ])),
            tools=self.tool_config,
            tool_choice='required',
        )
        response = completion.choices[0].message
        if response.refusal:
            logger.info("Refusal:", response.refusal)
        if response.content:
            logger.info(response.content)
        self.master.run_tools(response.tool_calls)
