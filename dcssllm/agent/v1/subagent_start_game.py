import logging
import typing

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from dcssllm.agent.util import *
from dcssllm.agent.v1.common_graph import BaseAgentState, attach_tool_nodes, create_chatbot_node
from dcssllm.agent.v1.general_instructions import *

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent

logger = logging.getLogger(__name__)


class AgentState(BaseAgentState):
    pass


class SubagentStartGame:
    """
    In charge of starting a new game or resuming an existing one.
    """
    def __init__(self, master: "V1Agent", llm: BaseChatModel):
        self.master = master
        self.tools = [
            self.master.tool_send_key_press
        ]
        
        def message_generator(state: AgentState):
            messages = prep_message([
                SystemMessage(GENERAL_AGENT_INTRO),
                SystemMessage("""
                    Current Objective: Start a new game, or resume an existing one. Prefer to resume an existing game
                    if there is one. Navigate the UI by interpreting the screen and sending the appropriate commands
                    to the game.

                    Choose the Minotaur Berserker class. Choose an axe as your starting weapon.
                """),
                *state["messages"]
            ])
            return messages, {}

        chatbot = create_chatbot_node(__name__, llm.bind_tools(self.tools), message_generator)
        graph_builder = StateGraph(AgentState)
        graph_builder.add_node("chatbot", chatbot)
        attach_tool_nodes(graph_builder, self.tools, "chatbot", END)
        
        graph_builder.add_edge(START, "chatbot")
        self.executor = graph_builder.compile()

    async def ai_turn(self):
        final_state = await self.executor.ainvoke({
            "messages": prep_message([
                HumanMessage(f"""
                    Use the arrow keys to select a menu entry. Use the 'ENTER' key to confirm your selection.
                    If there's a letter next to a menu entry, you can press that letter to select it.
                """),
                HumanMessage(f"The current screen is:\n\n{self.master.latest_screen}"),
            ]),
            "iteration": self.master.iterations,
        })

        logger.info(f"SubagentStartGame final_state: { {**final_state, "messages": None} }")
