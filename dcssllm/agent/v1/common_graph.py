import logging
from typing import Annotated, Any, Dict, Callable, Tuple, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import BaseTool
from typing_extensions import TypedDict

from dcssllm.agent.util import *
from dcssllm.agent.v1.general_instructions import *

logger = logging.getLogger(__name__)


def add_number(a: Optional[int], b: Optional[int]) -> Optional[int]:
    return (a or 0) + (b or 0)


class BaseAgentState(TypedDict):
    iteration: int
    messages: Annotated[list[BaseMessage], add_messages]
    _chatbot_message_number: Annotated[int, add_number]
    _n_input_tokens: Annotated[int, add_number]
    _n_output_tokens: Annotated[int, add_number]


def create_chatbot_node[T: BaseAgentState](
    name: str, llm: BaseChatModel, 
    bot_func: Callable[[T], Tuple[List[BaseMessage], T]]
):
    def chatbot(state: T):
        request, new_state = bot_func(state)
        log_llm_io(name, state["iteration"], state["_chatbot_message_number"], "prompt", request)
        response = llm.invoke(request)
        log_llm_io(name, state["iteration"], state["_chatbot_message_number"], "response", [response])

        if isinstance(response, AIMessage) and response.usage_metadata:
            incr_input_tokens = response.usage_metadata["input_tokens"]
            incr_output_tokens = response.usage_metadata["output_tokens"]
        else:
            incr_input_tokens = 0
            incr_output_tokens = 0

        return {
            **new_state,
            "_chatbot_message_number": 1,
            "_n_input_tokens": incr_input_tokens,
            "_n_output_tokens": incr_output_tokens,
            "messages": [response],
        }
    return chatbot


def attach_tool_nodes(graph_builder: StateGraph, tools: list[BaseTool], bot_node: str, message_node: str,
                      enable_terminal_edges: bool = True, message_key: str = "messages"):
    """
    Attach tool nodes to the specified bot node. If enable_terminal_edges is true, tool calls that include
    a tool with the return_direct flag set to true will be routed to the END node. Otherwise, they will be
    back routed to the bot node. Non-tool calls will be routed to the message_node.
    """
    tool_map = { tool.name: tool for tool in tools }

    def route_tools(state: Dict[str, Any]):
        ai_message = state[message_key][-1]
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            logger.info("=== TOOL CALL ===")
            logger.info(f"{ai_message.content}")
            logger.info(f"{ai_message.tool_calls}")

            if enable_terminal_edges:
                for tool_call in ai_message.tool_calls:
                    tool = tool_map.get(tool_call["name"], None)
                    if tool is not None and tool.return_direct:
                        logger.info(f"Tool call {tool_call} is terminal")
                        return f"_{bot_node}_tools_terminal"
            return f"_{bot_node}_tools"
        return message_node
    
    tool_node = ToolNode(tools)
    graph_builder.add_node(f"_{bot_node}_tools", tool_node)
    graph_builder.add_edge(f"_{bot_node}_tools", bot_node)
    graph_builder.add_conditional_edges(bot_node, route_tools)

    if enable_terminal_edges:
        graph_builder.add_node(f"_{bot_node}_tools_terminal", tool_node)
        graph_builder.add_edge(f"_{bot_node}_tools_terminal", END)