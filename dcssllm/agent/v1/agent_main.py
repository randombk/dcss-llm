
from typing import List
from logging import getLogger

from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from dcssllm.agent.util import *
from dcssllm.agent.base_agent import BaseAgent
from dcssllm.agent.v1.general_instructions import *
from dcssllm.agent.v1.subagent_current_objective import SubagentCurrentObjective
from dcssllm.agent.v1.subagent_final_action import SubagentFinalAction
from dcssllm.agent.v1.subagent_start_game import SubagentStartGame
from dcssllm.agent.v1.subagent_summarize_last_turn import SubagentSummarizeLastTurn
from dcssllm.agent.v1.tool import BaseTool
from dcssllm.agent.v1.tool_game_state import ToolGameState
from dcssllm.agent.v1.tool_longterm_memory import ToolLongTermMemory
from dcssllm.agent.v1.tool_send_key_press import ToolSendKeyPress
from dcssllm.agent.v1.tool_shortterm_memory import ToolShortTermMemory
from dcssllm.curses_utils import CursesApplication
from dcssllm.llmutils import LLMConfig


logger = getLogger(__name__)

class V1Agent(BaseAgent):
    def __init__(self, game: CursesApplication,
                 llm_default: LLMConfig,
                 llm_start_game: LLMConfig = None, llm_summarize_last_turn: LLMConfig = None, 
                 llm_current_objective: LLMConfig = None,
                 llm_final_action: LLMConfig = None):
        super().__init__()
        self.game = game

        self.game_state = None
        self.latest_screen = ""
        self.latest_text_only_screen = ""
        self.previous_screen = ""
        self.previous_text_only_screen = ""
        self.nothing_happened = False
        self.nothing_happened_keys = set()
        self.current_dialog = ""

        # Init tools - do before initializing subagents
        self.tool_send_key_press = ToolSendKeyPress(self, game)
        self.tool_longterm_memory = ToolLongTermMemory(self)
        self.tool_shortterm_memory = ToolShortTermMemory(self)
        self.tool_game_state = ToolGameState(self)
        self.tools: List[BaseTool] = [
            self.tool_send_key_press,
            self.tool_longterm_memory,
            self.tool_shortterm_memory,
            self.tool_game_state,
        ]

        # Subagents for running specific tasks
        self.subagent_start_game = SubagentStartGame(self, llm_start_game or llm_default)
        self.subagent_summarize_last_turn = SubagentSummarizeLastTurn(self, llm_summarize_last_turn or llm_default)
        self.subagent_current_objective = SubagentCurrentObjective(self, llm_current_objective or llm_default)
        self.subagent_final_action = SubagentFinalAction(self, llm_final_action or llm_default)


    def run_tools(self, tool_calls: List[ChatCompletionMessageToolCall]):
        for tool_call in (tool_calls or []):
            for tool in self.tools:
                tool.process_tool_call(tool_call)


    def on_new_screen(self, screen: str, text_only_screen: str):
        self.previous_screen = self.latest_screen
        self.previous_text_only_screen = self.latest_text_only_screen
        self.latest_screen = screen
        self.latest_text_only_screen = text_only_screen

        if self.tool_send_key_press.sent_key and self.previous_screen == self.latest_screen:
            logger.info(f"[STATE CHANGE] Setting 'Nothing Happened' Flag")
            self.nothing_happened = True
            self.nothing_happened_keys.add(self.tool_send_key_press.previous_key)
        else:
            self.nothing_happened = False
            self.nothing_happened_keys = set()

        # Try to infer if we're in a dialog or menu
        if "] set a skill target" in text_only_screen:
            self.current_dialog = "skills"
        elif ", Time: " in text_only_screen:
            self.current_dialog = "player_info"
        else:
            self.current_dialog = ""

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


    async def ai_turn(self):
        await super().ai_turn()
        # Remember this because we'l be resetting this shortly
        last_turn_sent_action = self.tool_send_key_press.sent_key

        for tool in self.tools:
            tool.on_new_turn()

        if self.game_state == "main_menu":
            await self.subagent_start_game.ai_turn()
            return

        if self.game_state == "main_game":
            if last_turn_sent_action:
                await self.subagent_summarize_last_turn.ai_turn()

            current_objective = await self.subagent_current_objective.ai_turn(
                what_happened_last_turn=self.subagent_summarize_last_turn.what_happened_last_turn,
            )
            await self.subagent_final_action.ai_turn(current_objective)


    def get_message_no_action(self):
        if self.nothing_happened:
            return {
                "role": "user",
                "content": trim_indent(f"""
                    You last action(s) did not seem to do anything. You have already tried the following
                    keys: [{', '.join(self.nothing_happened_keys)}] and nothing changed.

                    You should try something else instead. Do not repeat the same action.
                """),
            }
        else:
            return None
     
