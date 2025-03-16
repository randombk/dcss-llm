import typing
from typing import Dict, Optional, Any
from logging import getLogger

from openai import AsyncOpenAI
from dcssllm.agent.util import *
from dcssllm.agent.v1.general_instructions import *
from dcssllm.agent.v1.tool_game_state import Position
from dcssllm.llmutils import LLMConfig, strip_reasoning

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)

class SubagentAdvisorNavigation:
    """
    A subagent that provides information about where the player can go next.
    """
    def __init__(self, master: "V1Agent", llm: LLMConfig):
        self.master = master
        self.llm = llm
        self.client = AsyncOpenAI(base_url=llm.uri, api_key=llm.secret or 'NONE')
        self.navigation_history = []


    async def ai_turn(self, what_happened_last_turn: str, current_objective: str) -> Optional[Dict[Any, Any]]:
        cur_state = self.master.tool_game_state.current_state
        if cur_state is None:
            return None

        player_pos = cur_state.player_pos
        local_map = cur_state.get_map()

        # Check with directions are walkable
        direction_offsets = {
            "UP": (0, -1),
            "DOWN": (0, 1),
            "LEFT": (-1, 0),
            "RIGHT": (1, 0),
            "TOP_LEFT": (-1, -1),
            "TOP_RIGHT": (1, -1),
            "BOTTOM_LEFT": (-1, 1),
            "BOTTOM_RIGHT": (1, 1)
        }
        walkable_directions = []
        for direction, offset in direction_offsets.items():
            new_pos = cur_state.get_cell(Position(player_pos.x + offset[0], player_pos.y + offset[1]))
            if new_pos and new_pos.traversable:
                walkable_directions.append(direction)

        additional_instructions = trim_indent(f"""
            I am currently located at {player_pos}.
            The only directions I can walk in are: {', '.join(walkable_directions)}. I can not walk in other directions.
        """)

        # Format the last 50 rows of navigation_history as an agent conversation.
        history = []
        for i, entry in enumerate(self.navigation_history[-50:]):
            history.append({
                "role": "user",
                "content": trim_indent(f"""
                    Turn {entry['turn']}:
                        I am at {entry['player_pos']}
                        The only directions I can walk in are: {', '.join(entry['walkable_directions'])}.
                        My objective is: {entry['objective']}
                """)
            })
            history.append({
                "role": "assistant",
                "content": entry['path_instructions']
            })

        completion = await self.client.chat.completions.create(
            model=self.llm.model,
            messages=prep_message(__name__, notnull([
                {
                    "role": "system",
                    "content": GENERAL_AGENT_INTRO,
                },
                {
                    "role": "user",
                    "content": trim_indent(f"""
                        Your job is to plan out a path to your next objective. Look at the map around you and decide where
                        you want to go next. In particular, consider the walkable directions and whether you need to backtrack
                        or take a different path to reach your objective.

                        Use the position history to help you understand where you've been and whether you're walking in circles.
                        If you are, then recommend that you take a different path, even if it seems longer.

                        Only write direction information. For example, you could say these types of things:
                        * "There's a room to the right. I need to backtrack to the top left to get to the entrance."
                        * "I have walked into a dead end with no easy path to my objective."
                        Don't limit yourself to these statements. Write full sentences. Do not call tools.
                    """),
                },
                {
                    "role": "assistant",
                    "content": "OK, I am ready.",
                },
                *history,
                {
                    "role": "user",
                    "content": f"The current turn is: {self.master.iterations}",
                },
                self.master.tool_longterm_memory.get_memory_message(),
                self.master.tool_shortterm_memory.get_memory_message(),
                {
                    "role": "user",
                    "content": f"My current objective is: {current_objective}",
                },
                {
                    "role": "user",
                    "content": f"Last turn, I: {what_happened_last_turn}",
                } if what_happened_last_turn != "" else None,
                {
                    "role": "user",
                    "content": "The current map is:\n\n```\n" + local_map + "\n```\n",
                },
                {
                    "role": "user",
                    "content": "I am located at '@'. '#' represents walls, '.' represents walkable areas, and ' ' represents unknown areas.",
                },
                {
                    "role": "user",
                    "content": additional_instructions,
                },
            ])),
        )
        response = completion.choices[0].message
        if response.refusal:
            logger.info("Refusal:", response.refusal)

        path_instructions = strip_reasoning(response.content or "")
        logger.info(f"Pathing instructions: {path_instructions}")

        self.navigation_history.append({
            "turn": self.master.iterations,
            "objective": current_objective,
            "player_pos": player_pos,
            "walkable_directions": walkable_directions,
            "path_instructions": path_instructions,
        })

        return {
            "name": "navigation",
            "path_instructions": path_instructions,
            "walkable_directions": walkable_directions,
            "message": additional_instructions + trim_indent(f"""
                {path_instructions}
            """)
        }
