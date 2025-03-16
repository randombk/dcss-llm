import typing
from logging import getLogger

from openai import AsyncOpenAI
from dcssllm.agent.util import *
from dcssllm.agent.v1.general_instructions import *
from dcssllm.llmutils import LLMConfig, strip_reasoning

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)

class SubagentSummarizeLastTurn:
    def __init__(self, master: "V1Agent", llm: LLMConfig):
        self.master = master
        self.llm = llm
        self.client = AsyncOpenAI(base_url=llm.uri, api_key=llm.secret or 'NONE')
        self.what_happened_last_turn = ""


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
                    "content": GAME_UI_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": KEY_BINDING_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": trim_indent(f"""
                        Your job is to summarize what happened in the last turn. I will give you the previous
                        screen, the action(s) you took, and the current screen. Compare the two screens and determine
                        what changed.
                    """),
                },
                {
                    "role": "user",
                    "content": "The previous screen was:\n\n```\n" + self.master.previous_text_only_screen + "\n```\n",
                },
                {
                    "role": "user",
                    "content": f"You pressed the following key: '{self.master.tool_send_key_press.previous_key}'",
                },
                {
                    "role": "user",
                    "content": "The current screen is now:\n\n```\n" + self.master.latest_text_only_screen + "\n```\n",
                },
                self.master.tool_game_state.get_state_diff_message(),
                self.master.get_message_no_action(),
                {
                    "role": "user",
                    "content": trim_indent("""
                        Write a one or two sentence summary of what happened in the last turn. Do not write anything else.
                        
                        For example, you could say these types of things (but don't constrain yourself to these quotes):
                            "I moved up and revealed the interior of a room to my left."
                            "I moved down to stand next to an open door."
                            "I picked up a sword from the ground."
                            "I opened the inventory menu."
                            "I tried to move to the left, but nothing happened."

                        Be careful when you say you're 'next to' something. Only say that if your character is actually
                        right next to the thing you're talking about.
                        
                        Pay attention to any new information or messages that appeared on the screen.
                        
                        Be concise and to the point. Focus on the interpretation of what happened, rather than a mechanical diff of the screen.
                    """)
                }
            ])),
        )
        response = completion.choices[0].message
        if response.refusal:
            logger.info("Refusal:", response.refusal)

        self.what_happened_last_turn = strip_reasoning(response.content or "")
        logger.info(response.content)
        return self.what_happened_last_turn
