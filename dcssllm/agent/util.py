import textwrap
from typing import List, Any, Optional
from openai.types.chat import ChatCompletionMessageParam


def consolidate(value: List[ChatCompletionMessageParam]) -> List[ChatCompletionMessageParam]:
    """
    Conversation roles must alternate user/assistant/user/assistant...

    This function consolidates adjacent messages of the same role into a single message.
    """
    if not value:
        return value

    consolidated = [value[0]]
    for message in value[1:]:
        if message['role'] == consolidated[-1]['role']:
            consolidated[-1]['content'] += "\n\n" + message['content']
        else:
            consolidated.append(message)
    return consolidated


def notnull(value: List[Optional[Any]]) -> List[Any]:
    return [x for x in value if x is not None]


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
    