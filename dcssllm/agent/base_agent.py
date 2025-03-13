from abc import ABC, abstractmethod
from logging import getLogger

from dcssllm.curses_utils import CursesApplication

logger = getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self):
        super().__init__()
        self.iterations = 0
    
    @abstractmethod
    def on_new_screen(self, screen: str):
        pass

    @abstractmethod
    async def ai_turn(self):
        self.iterations += 1
        logger.info(f"\n\n\nBEGIN ITERATION {self.iterations}\n\n\n")
