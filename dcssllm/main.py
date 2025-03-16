import asyncio
import logging
import time
import sys
import json
import signal
import os

from dcssllm.agent.v1.agent_main import V1Agent
from dcssllm.curses_utils import CursesApplication
from dcssllm.keycodes import Keycode
from dcssllm.llmutils import LLMConfig


def configure_logging():
    # Create a console handler that outputs DEBUG level logs.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Get the top-level dcssllm logger.
    dcssllm_logger = logging.getLogger('dcssllm')
    dcssllm_logger.setLevel(logging.DEBUG)

    # Attach the console handler to the dcssllm logger.
    dcssllm_logger.addHandler(console_handler)


async def main():
    command = "crawl/crawl-ref/source/crawl"

    # HACK: I'm going to read API keys from the `llm2sh` configuration for now,
    # as I don't want to implement a new configuration file for this project.

    # Resolve relative path to '~'
    with open(os.path.expanduser("~/.config/llm2sh/llm2sh.json")) as f:
        secrets = json.load(f)
        local_api_key = secrets.get("local_api_key", "")
        openai_api_key = secrets.get("openai_api_key", "")
        anthropic_api_key = secrets.get("anthropic_api_key", "")
        openrouter_api_key = secrets.get("openrouter_api_key", "")
        groq_api_key = secrets.get("groq_api_key", "")
        cerebras_api_key = secrets.get("cerebras_api_key", "")
        gemini_api_key = secrets.get("gemini_api_key", "")

    #
    # Define common LLMs we can use
    #
    llm_local = LLMConfig('http://127.0.0.1:8080/v1/', local_api_key, 'local')

    # Groq; Limit: 500K tokens/day, each
    groq_llama32_8b = LLMConfig('https://api.groq.com/openai/v1/', groq_api_key, 'llama-3.1-8b-instant')
    groq_llama3_70b_8192 = LLMConfig('https://api.groq.com/openai/v1/', groq_api_key, 'llama3-70b-8192')
    groq_llama3_8b_8192 = LLMConfig('https://api.groq.com/openai/v1/', groq_api_key, 'llama3-8b-8192')

    # Groq; No token limit; 1K queries/day
    # groq_qwen_25_32b = LLMConfig('https://api.groq.com/openai/v1/', groq_api_key, 'qwen-2.5-32b')
    groq_deepseek_r1_llama70 = LLMConfig('https://api.groq.com/openai/v1/', groq_api_key, 'deepseek-r1-distill-llama-70b')

    # Cerebras; Limit: 1M tokens/day, each, 8192 context limit
    cerebras_llama3_8b = LLMConfig('https://api.cerebras.ai/v1/', cerebras_api_key, 'llama3.1-8b')
    cerebras_llama3_70b = LLMConfig('https://api.cerebras.ai/v1/', cerebras_api_key, 'llama3.3-70b')
    # cerebras_deepseek_r1_llama70 = LLMConfig('https://api.cerebras.ai/v1/', cerebras_api_key, 'deepseek-r1-distill-llama-70b')

    # Gemini;

    # Limit: 15 RPM 1500 req/day
    gemini_2_flash = LLMConfig('https://generativelanguage.googleapis.com/v1beta/openai/', gemini_api_key, 'gemini-2.0-flash')

    # Limit: 30 RPM 1500 req/day
    gemini_2_lite_flash = LLMConfig('https://generativelanguage.googleapis.com/v1beta/openai/', gemini_api_key, 'gemini-2.0-flash')

    min_seconds_between_actions = 3
    configure_logging()

    with CursesApplication(command, init_wait_secs=2) as app:
        agent = V1Agent(
            game=app,
            llm_default=llm_local,
            # llm_default=gemini_2_flash,
            # llm_start_game=llm_local,
            # llm_summarize_last_turn=groq_deepseek_r1_llama70,
            # llm_current_objective=groq_llama3_70b_8192,
            # llm_final_action=groq_deepseek_r1_llama70,
        )

        # register handler for when the user ctrl-c quits python
        def signal_handler(sig, frame):
            print("Quitting...")
            app.send_keycode(Keycode.ESC)
            time.sleep(0.25)
            app.send_keycode(Keycode.ESC)
            time.sleep(0.25)
            app.send_keycode(Keycode.CTRL_S)
            time.sleep(0.25)
            app.send_keycode(Keycode.ESC)
            time.sleep(0.25)
            app.send_keycode(Keycode.ESC)
            time.sleep(0.25)
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)

        # Main AI Loop
        while True:
            last_action_time = time.time()
            app.await_update()
            screen = app.get_current_screen()
            text_only_screen = '\n'.join(app.screen.display)

            sys.stdout.write(screen)
            with open('tmp/screen.log', 'w') as f:
                f.write(screen)
            with open('tmp/text_only_screen.log', 'w') as f:
                f.write(text_only_screen)

            agent.on_new_screen(screen, text_only_screen)
            await agent.ai_turn()

            await asyncio.sleep(max(0, min_seconds_between_actions - (time.time() - last_action_time)))

if __name__ == "__main__":
    asyncio.run(main())

