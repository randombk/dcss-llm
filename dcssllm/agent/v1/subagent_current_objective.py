import typing
from logging import getLogger

from openai import AsyncOpenAI
from dcssllm.agent.util import *
from dcssllm.agent.v1.general_instructions import *
from dcssllm.llmutils import LLMConfig, strip_reasoning

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)

class SubagentCurrentObjective:
    def __init__(self, master: "V1Agent", llm: LLMConfig):
        self.master = master
        self.llm = llm
        self.client = AsyncOpenAI(base_url=llm.uri, api_key=llm.secret or 'NONE')
        self.current_objective = "I don't have an objective yet - I should pick one."
        self.last_objective_change = self.master.iterations


    async def ai_turn(self, what_happened_last_turn: str):
        completion = await self.client.chat.completions.create(
            model=self.llm.model,
            messages=consolidate(notnull([
                {
                    "role": "system",
                    "content": GENERAL_AGENT_INTRO,
                },
                {
                    "role": "user",
                    "content": GAME_UI_INSTRUCTIONS,
                },
                self.master.tool_longterm_memory.get_memory_message(),
                self.master.tool_shortterm_memory.get_memory_message(),
                {
                    "role": "user",
                    "content": "The current screen is:\n\n" + self.master.latest_screen,
                },
                {
                    "role": "user",
                    "content": f"Last turn, you: {what_happened_last_turn}",
                } if what_happened_last_turn != "" else None,
                {
                    "role": "user",
                    "content": trim_indent(f"""
                        Your job is to decide what you want to do in the next few turns. Look around you, think about what
                        long-term plans you have, and decide what you want to do next. You can change your mind later.
                        You should always have an objective in mind, even if it's just to explore the map or to find the stairs.
                        
                        Currently, your objective is set to "{self.current_objective}".
                        You have been doing this objective for the last {self.master.iterations - self.last_objective_change} turns.
                        If you've been at this a long time without notable results, consider changing your objective.

                        If you want to keep this objective, write "KEEP_CURRENT" and nothing else. Reasons you may want to change your objective:
                        - You've completed your current objective
                        - You're in a new situation that requires a new objective
                        - You have new information that changes your priorities
                        - You've thought of a better plan

                        However, prefer to keep the current objective so as to give yourself a consistent plan to follow.
                        If you want to change your objective, write one or two sentences describing your new objective.

                        Example objective statements include:
                        - "Explore the unexplored parts of the map to the bottom right."
                        - "Walk to the stairs on the left and go down to the next floor."
                        - "Run away from the monster to the right and heal up."
                        - "Walk to the pile of gold to the right and pick it up."
                        Don't feel constrained by these examples.

                        Just write the objective. Don't write anything else, such as "I want to" or "I will".

                    """),
                },
            ])),
        )
        response = completion.choices[0].message
        if response.refusal:
            logger.info("Refusal:", response.refusal)

        if 'KEEP_CURRENT' in response.content:
            logger.info(f"Keeping current objective: {self.current_objective}")
            return self.current_objective
        else:    
            self.current_objective = strip_reasoning(response.content or "")
            logger.info(f"New objective: {self.current_objective}")
            self.last_objective_change = self.master.iterations
        return self.current_objective
