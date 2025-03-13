import re
from dataclasses import dataclass

@dataclass
class LLMConfig:
    uri: str
    secret: str
    model: str


def strip_reasoning(message: str) -> str:
    # Remove the text between <thinking> and </thinking> tags.
    return re.sub(r"<thinking>.*?</thinking>", "", message)