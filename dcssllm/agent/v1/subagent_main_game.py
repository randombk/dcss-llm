import logging
from typing import List, TYPE_CHECKING

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph import StateGraph, START, END

from dcssllm.agent.util import *
from dcssllm.agent.v1.common_graph import BaseAgentState, attach_tool_nodes, create_chatbot_node
from dcssllm.agent.v1.general_instructions import *

if TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent

logger = logging.getLogger(__name__)


class AgentState(BaseAgentState):
    previous_turn_summary: List[BaseMessage]


class SubagentMainGame:
    """
    In charge of starting a new game or resuming an existing one.
    """
    def __init__(self, master: "V1Agent", llm: BaseChatModel):
        self.master = master
        self.tools = [
            self.master.tool_send_key_press,
            self.master.tool_game_state,
            self.master.tool_write_long_term_memory,
        ]
        self._previous_turn_actions = []

        def message_generator(state: AgentState):
            force_action = None
            if state['_chatbot_message_number'] > 10:
                force_action = HumanMessage(f"""
                    Alright, you've been thinking for too long.
                    YOU MUST SEND A KEY PRESS NOW.
                """),

            messages = prep_message([
                SystemMessage(GENERAL_AGENT_INTRO),
                SystemMessage(GAME_UI_INSTRUCTIONS),
                SystemMessage(CHARACTER_PLAYSTYLE_INSTRUCTIONS),
                SystemMessage(KEY_BINDING_INSTRUCTIONS),
                *state["previous_turn_summary"],
                HumanMessage(f"The current turn is {state['iteration']}."),
                self.master.long_term_memory.create_message(),
                *self.master.tool_game_state.create_message(),
                *state["messages"],
                force_action,
            ])
            return messages, {}

        chatbot = create_chatbot_node(__name__, llm.bind_tools(self.tools), message_generator)
        graph_builder = StateGraph(AgentState)
        graph_builder.add_node("chatbot", chatbot)

        # In the main game, the only way to end the turn is to send a key press
        # Normal non-tool messages should not end the turn. Instead, encourage
        # the agent to keep thinking.
        def dummy_user_message(_: AgentState):
            return {
                "messages": [
                    HumanMessage("Ok, keep thinking. What do you want to do next? You should call at least one tool."),
                ],
            }
        graph_builder.add_node("dummy_user_message", dummy_user_message)
        graph_builder.add_edge("dummy_user_message", "chatbot")
        attach_tool_nodes(graph_builder, self.tools, "chatbot", "dummy_user_message")

        graph_builder.add_edge(START, "chatbot")
        self.executor = graph_builder.compile()

    async def ai_turn(self):
        formatted_previous_turn_actions = []
        for (iteration, screen, message) in self._previous_turn_actions[-20:]:
            formatted_previous_turn_actions.extend(prep_message([
                HumanMessage(f"Turn {iteration}:"),
                HumanMessage(f"The current screen is:\n\n{screen}"),
            ]))
            formatted_previous_turn_actions.append(message)

        final_state = await self.executor.ainvoke({
            "messages": prep_message([
                HumanMessage("""
                    You're in-game now. Look at the information you've been given and form a strategy for
                    how to play the game. You don't know much about the game, so explore and learn from your
                    experiences.
                             
                    Take your time. Strategize. Decisions now can have long-term consequences. Think about
                    what you want to do, short and medium term objectives, and long term goals.
                    Save what you have learned in your long-term memory.
                    Don't be in a rush to press a button.
                             
                    As you learn more about the game (i.e. how to use tools or perform actions), update your
                    long-term memory to remind yourself of what you've learned. At the start of each turn, you
                    should think "What do I know now that I didn't know before?" and "Is this something worth
                    writing down in my long-term memory?"
                             
                    If you have nothing better to do, using autoexplore ('o')is a good idea. Once you have explored
                    the area, proceed to the next floor.
                """),
                HumanMessage(f"The current screen is:\n\n{self.master.latest_screen}"),
                HumanMessage(f"Without any formatting, the current screen is:\n\n{self.master.latest_text_only_screen}"),
            ]),
            "iteration": self.master.iterations,
            "previous_turn_summary": formatted_previous_turn_actions,
        })

        last_ai_message = find_last_match(final_state["messages"], lambda m: m.type == "ai")
        self._previous_turn_actions.append((
            self.master.iterations,
            self.master.latest_text_only_screen,
            last_ai_message,
        ))

        logger.info(f"SubagentMainGame final_state: { {**final_state, "messages": None, "previous_turn_summary": None} }")
