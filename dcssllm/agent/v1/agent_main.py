
from typing import List
from logging import getLogger

from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel

from dcssllm.agent.util import *
from dcssllm.agent.base_agent import BaseAgent
from dcssllm.agent.v1.general_instructions import *
from dcssllm.agent.v1.subagent_main_game import SubagentMainGame
from dcssllm.agent.v1.subagent_start_game import SubagentStartGame
from dcssllm.agent.v1.tool import StatefulTool
from dcssllm.agent.v1.tool_game_state import ToolGameState
from dcssllm.agent.v1.tool_longterm_memory import LongTermMemory, ToolWriteLongTermMemory
from dcssllm.agent.v1.tool_send_key_press import ToolSendKeyPress
from dcssllm.curses_utils import CursesApplication


logger = getLogger(__name__)

class V1Agent(BaseAgent):
    def __init__(self, game: CursesApplication,
                 llm_default: BaseChatModel,
                 llm_start_game: BaseChatModel = None, 
                 llm_main_game: BaseChatModel = None,):
        super().__init__()
        self.game = game # Connection to the game instance

        # Current game mode (main_menu, main_game, etc)
        self.game_state = ""

        # Screen data and history
        self.latest_screen = ""
        self.latest_text_only_screen = ""
        self.previous_screen = {}
        self.previous_text_only_screen = {}

        # Utility to track if the last action didn't do anything
        self.nothing_happened = False
        self.nothing_happened_keys = set()
        
        # Init tools - do before initializing subagents
        self.tool_send_key_press = ToolSendKeyPress(self, game)
        
        self.long_term_memory = LongTermMemory()
        self.tool_write_long_term_memory = ToolWriteLongTermMemory(self, self.long_term_memory)

        self.tool_game_state = ToolGameState(self)
        self.tools: List[StatefulTool] = [
            self.tool_send_key_press,
            self.tool_game_state,
            self.tool_write_long_term_memory,
        ]

        # Subagents for running specific tasks
        self.subagent_start_game = SubagentStartGame(self, llm_start_game or llm_default)
        self.subagent_main_game = SubagentMainGame(self, llm_main_game or llm_default)

    async def ai_turn(self, screen: str, text_only_screen: str):
        await super().ai_turn()
        self._on_new_screen(screen, text_only_screen)
        
        # Remember this because updating tool state will reset it
        last_turn_sent_action = self.tool_send_key_press._sent_key

        for tool in self.tools:
            tool.on_new_turn()

        if self.game_state == "main_menu":
            await self.subagent_start_game.ai_turn()
            return

        if self.game_state == "main_game":
            await self.subagent_main_game.ai_turn()


    def get_message_no_action(self):
        if self.nothing_happened:
            return HumanMessage(trim_indent(f"""
                You last action(s) did not seem to do anything. You have already tried the following
                keys: [{', '.join(self.nothing_happened_keys)}] and nothing changed.

                You should try something else instead. Do not repeat the same action.
            """))
        else:
            return None


    def _on_new_screen(self, screen: str, text_only_screen: str):
        self.latest_screen = screen
        self.latest_text_only_screen = text_only_screen
        self.previous_screen[self.iterations] = self.latest_screen
        self.previous_text_only_screen[self.iterations] = self.latest_text_only_screen

        if self.tool_send_key_press._sent_key and self.previous_screen == self.latest_screen:
            logger.info(f"[STATE CHANGE] Setting 'Nothing Happened' Flag")
            self.nothing_happened = True
            self.nothing_happened_keys.add(self.tool_send_key_press._previous_key)
        else:
            self.nothing_happened = False
            self.nothing_happened_keys = set()

        # Detect if we're in the main menu
        if "Hello, welcome to Dungeon Crawl Stone Soup" in text_only_screen and self.game_state != "main_menu":
            logger.info(f"[STATE CHANGE] We're in the main menu")
            self.game_state = "main_menu"
            return

        # Detect the main game screen
        if "Health:" in text_only_screen and "Magic:" in text_only_screen and self.game_state != "main_game":
            logger.info(f"[STATE CHANGE] We're in the main game")
            self.game_state = "main_game"
            return
     
