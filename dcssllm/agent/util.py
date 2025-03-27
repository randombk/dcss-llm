import textwrap
from typing import List, Any, Optional
from langchain_core.messages.base import BaseMessage
from langchain_core.messages.tool import ToolMessage
from langchain_core.messages.ai import AIMessage

def notnull(value: List[Optional[Any]]) -> List[Any]:
    return [x for x in value if x is not None]

def find_last_match(array, filter_func):
    """
    Returns the last element in the array that satisfies the filter function.
    If no element matches, returns None.
    
    Args:
        array: The list to search through
        filter_func: A function that takes an element and returns True/False
        
    Returns:
        The last matching element or None if no match is found
    """
    for element in reversed(array):
        if filter_func(element):
            return element
    return None

def trim_indent(text: str) -> str:
    """
    Mimics Kotlin's trimIndent:
    - If the first or last line is blank, they are removed.
    - The minimal indent (whitespace) common to all non-blank lines is computed and removed.

    Args:
        text: The input multi-line string.

    Returns:
        The string with common indent removed.
    """
    # Split text into individual lines
    lines = text.splitlines()

    # Remove the first line if it is blank.
    if lines and lines[0].strip() == "":
        lines = lines[1:]
    # Remove the last line if it is blank.
    if lines and lines[-1].strip() == "":
        lines = lines[:-1]

    # Join the remaining lines back into a single string.
    trimmed_text = "\n".join(lines)

    # Use textwrap.dedent to remove the common leading whitespace.
    return textwrap.dedent(trimmed_text)


def prep_message(value: List[BaseMessage]) -> List[BaseMessage]:
    """
    Conversation roles must alternate user/assistant/user/assistant...

    This function consolidates adjacent messages of the same role into a single message and applies trim_indent to the content.
    """
    value = notnull(value)
    if not value:
        return value

    value[0].content = trim_indent(value[0].content)
    consolidated = [value[0]]
    for message in value[1:]:
        if message.type == consolidated[-1].type and message.type != "tool":
            consolidated[-1].content += "\n\n" + trim_indent(message.content)
        else:
            consolidated.append(message)

    return consolidated

def log_llm_io(
    agent_name: str, iteration: int, chatbot_message_number: int, 
    type: str, messages: List[BaseMessage],
):
    agent_name = agent_name.replace("/", "__")
    with open(f"tmp/agent/{agent_name}-{iteration}-{chatbot_message_number}.{type}.log", "w") as f:
        for message in messages:
            f.write(f"===== {message.type.upper()} =====\n")
            f.write(f"{message.content}\n")

            if isinstance(message, AIMessage):
                if message.tool_calls:
                    f.write(f"Tool Calls: {message.tool_calls}\n")
                f.write(f"Usage Metadata: {message.usage_metadata}\n")

            if isinstance(message, ToolMessage):
                f.write(f"Tool Call ID: {message.tool_call_id}\n")

            f.write("=====\n\n")
