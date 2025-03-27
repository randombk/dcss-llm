import asyncio
import logging
import time
import sys
import json
import signal
import os

from langchain.chat_models import init_chat_model

from dcssllm.agent.v1.agent_main import V1Agent
from dcssllm.curses_utils import CursesApplication
from dcssllm.non_consuming_rate_limiter import NonConsumingRateLimiter
from dcssllm.keycodes import Keycode
from dcssllm.quota_aware_router import QuotaAwareRouter

logger = logging.getLogger(__name__)

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
        local_api_key = secrets.get("local_api_key", "NONE")
        openai_api_key = secrets.get("openai_api_key", "")
        anthropic_api_key = secrets.get("anthropic_api_key", "")
        openrouter_api_key = secrets.get("openrouter_api_key", "")
        groq_api_key = secrets.get("groq_api_key", "")
        cerebras_api_key = secrets.get("cerebras_api_key", "")
        gemini_api_key = secrets.get("gemini_api_key", "")

    llm = QuotaAwareRouter([
        #
        # Prefer Gemini when available
        #

        # Gemini 2 Flash
        (
            init_chat_model(
                'gemini-2.0-flash',
                model_provider="openai",
                openai_api_base='https://generativelanguage.googleapis.com/v1beta/openai/',
                openai_api_key=gemini_api_key,
            ),
            [
                NonConsumingRateLimiter(requests_per_second=15/60, max_bucket_size=10)
            ]
        ),

        # Gemini 2 Flash Lite
        (
            init_chat_model(
                'gemini-2.0-flash-lite',
                model_provider="openai",
                openai_api_base='https://generativelanguage.googleapis.com/v1beta/openai/',
                openai_api_key=gemini_api_key,
            ),
            [
                NonConsumingRateLimiter(requests_per_second=30/60, max_bucket_size=10)
            ]
        ),

        # Gemini 2 Flash Exp
        (
            init_chat_model(
                'gemini-2.0-flash-exp',
                model_provider="openai",
                openai_api_base='https://generativelanguage.googleapis.com/v1beta/openai/',
                openai_api_key=gemini_api_key,
            ),
            [
                NonConsumingRateLimiter(requests_per_second=10/60, max_bucket_size=10)
            ]
        ),
        
        # Local: slow, 32K context window, various models
        # Note: llama.cpp has issues where models can't produce content while also calling tools in the same turn.
        (
            init_chat_model(
                'local',
                model_provider="openai",
                openai_api_base='http://127.0.0.1:5001/v1/',
                openai_api_key=local_api_key or "NONE",
                # Llama.cpp has issues with streaming with tool calls
                disable_streaming=True 
            ),
            []
        ),
    ])

    min_seconds_between_actions = 3
    configure_logging()

    with CursesApplication(command, init_wait_secs=2) as app:
        agent = V1Agent(
            game=app,
            llm_default=llm,
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
        last_action_time = time.time()
        while True:
            # Wait for screen to stabilize
            # This is needed to support some commands that take a while to execute
            # (i.e. auto-explore and auto-move)
            while True:
                await app.await_update()
                screen1 = app.get_current_screen()
                await app.await_update(0.5)
                screen2 = app.get_current_screen()
                if screen1 == screen2:
                    break
                else:
                    logger.debug("Screen changed - assuming the game is still updating")
            
            # Get the screen
            screen = screen2
            text_only_screen = '\n'.join(app.screen.display)

            sys.stdout.write(screen)
            with open('tmp/screen.log', 'w') as f:
                f.write(screen)
            with open('tmp/text_only_screen.log', 'w') as f:
                f.write(text_only_screen)

            await agent.ai_turn(screen, text_only_screen)

            await asyncio.sleep(max(0, min_seconds_between_actions - (time.time() - last_action_time)))
            last_action_time = time.time()

if __name__ == "__main__":
    asyncio.run(main())

