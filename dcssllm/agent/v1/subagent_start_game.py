import typing
from logging import getLogger

from langchain_core.language_models.chat_models import BaseChatModel
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


from dcssllm.agent.util import *
from dcssllm.agent.v1.general_instructions import *

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent

logger = getLogger(__name__)


class SubagentStartGame:
    """
    In charge of starting a new game or resuming an existing one.
    """
    def __init__(self, master: "V1Agent", llm: BaseChatModel):
        self.master = master
        self.llm = llm

        self.tools = [
            self.master.tool_send_key_press
        ]

        self.prompt = ChatPromptTemplate.from_messages([
            # ("system", GENERAL_AGENT_INTRO),
            ("system", GENERAL_AGENT_INTRO + trim_indent("""
                Current Objective: Start a new game, or resume an existing one. Navigate the UI by interpreting
                the screen and sending the appropriate commands to the game.

                Choose the Minotaur Berserker class. Choose an axe as your starting weapon.

                IMPORTANT: Prefer to resume an existing game if there is one.

                YOU SHOULD ONLY OUTPUT A SINGLE KEY PRESS TO THE GAME VIA THE TOOL CALL.
            """)),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", trim_indent("""
                Use the arrow keys to select a menu entry. Use the 'ENTER' key to confirm your selection.
                If there's a letter next to a menu entry, you can press that letter to select it.

                The current screen is:

                {cur_screen}
            """)),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        # Create the agent
        self.agent = create_tool_calling_agent(llm=self.llm, tools=self.tools, prompt=self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    async def ai_turn(self):
        # Prepare the messages
        # messages = [
        #     HumanMessage(content=f"The current screen is:\n\n{self.master.latest_screen}")
        # ]

        # Add no_action message if it exists
        # no_action = self.master.get_message_no_action()
        # if no_action:
        #     messages.append(HumanMessage(content=no_action["content"]))

        # Add the nothing_happened message if needed
        # if self.master.nothing_happened:
        #     messages.append(HumanMessage(content="""
        #         Use the arrow keys to select a menu entry. Use the 'ENTER' key to confirm your selection.
        #         If there's a letter next to a menu entry, you can press that letter to select it.
        #     """))

        # Run the agent
        response = await self.agent_executor.ainvoke({
            "cur_screen": self.master.latest_screen,
        })


        # print(f"ContentString: {response}")

        # Log the response
        # if response:
        #     logger.info(response)

        # Process any tool calls
        # if hasattr(response, 'tool_calls'):
        #     self.master.run_tools(response.tool_calls)
