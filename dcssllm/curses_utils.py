import asyncio
import os
import time
import pty
import subprocess
import fcntl
import termios
import struct

import pyte

from dcssllm.keycodes import Keycode

FG_COLORS = {
    "default": "39",
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
}
BG_COLORS = {
    # "default": "49",
    "default": "40", # DCSS default background color is 40
    "black": "40",
    "red": "41",
    "green": "42",
    "yellow": "43",
    "blue": "44",
    "magenta": "45",
    "cyan": "46",
    "white": "47",
}

class CursesApplication:
    def __init__(self, command, cols=80, rows=24, init_wait_secs=1):
        self.command = command
        self.cols = cols
        self.rows = rows
        self.init_wait_secs = init_wait_secs
        self.master = None
        self.process = None
        self.screen = None
        self.stream = None

    def __enter__(self):
        # Create a pseudo-terminal
        self.master, slave = pty.openpty()
        
        # Set terminal size on the slave
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", self.rows, self.cols, 0, 0))
        
        # Start the process
        self.process = subprocess.Popen(
            self.command,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            shell=True,
            preexec_fn=os.setsid,

            # xterm doesn't seem to handle arrow keys correctly
            env=dict(os.environ, TERM='rxvt')
        )

        # Close the slave file descriptor as the child process now has it
        os.close(slave)

        # Set the master to non-blocking mode
        flags = fcntl.fcntl(self.master, fcntl.F_GETFL)
        fcntl.fcntl(self.master, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Set up a pyte screen to emulate a terminal
        self.screen = pyte.Screen(self.cols, self.rows)
        self.stream = pyte.ByteStream(self.screen)

        # Give the application time to initialize
        time.sleep(self.init_wait_secs)
        
        # Initialize the screen with the output
        self._feed_terminal_output()
        return self

    # Clean up the pseudo-terminal
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.process.terminate()
        os.close(self.master)
    
    def send_key(self, key: str):
        if key == 'UP':
            os.write(self.master, b'\x1b[A')
        elif key == 'DOWN':
            os.write(self.master, b'\x1b[B')
        elif key == 'LEFT':
            os.write(self.master, b'\x1b[D')
        elif key == 'RIGHT':
            os.write(self.master, b'\x1b[C')
        elif key == 'ENTER':
            os.write(self.master, b'\r')
        else:
            os.write(self.master, key.encode())

    def send_keycode(self, key: Keycode):
        os.write(self.master, key.value)

    def send_text(self, key: str):
        os.write(self.master, key.encode())

    async def await_update(self, delay: float = 0):
        if delay > 0:
            await asyncio.sleep(delay)
        self._feed_terminal_output()

    def get_current_screen(self):
        reset = "\x1b[0m"
        output_lines = []

        for y in sorted(self.screen.buffer.keys()):
            line = self.screen.buffer[y]
            current_fg = None
            current_bg = None
            current_bold = False
            line_str = ""

            for col in range(self.screen.columns):
                cell = line[col]
                
                cell_fg = cell.fg
                cell_bg = cell.bg
                codes = []
                
                # If the foreground changed, add its code.
                if cell_fg != current_fg:
                    codes.append(FG_COLORS.get(cell_fg, FG_COLORS["default"]))
                    current_fg = cell_fg
                
                # If the background changed, add its code.
                if cell_bg != current_bg:
                    codes.append(BG_COLORS.get(cell_bg, BG_COLORS["default"]))
                    current_bg = cell_bg
                
                if cell.bold != current_bold:
                    codes.append("1" if cell.bold else "22")
                    current_bold = cell.bold

                if codes:
                    ansi_seq = "\x1b[" + ";".join(codes) + "m"
                    line_str += ansi_seq

                line_str += cell.data
            
            # Reset at end of line.
            # line_str += reset
            
            output_lines.append(line_str)
        return "\n".join(output_lines) + reset + "\n"

    def _feed_terminal_output(self):
        """Read from the file descriptor and feed the data to the pyte stream."""
        try:
            # Read all available data
            while True:
                data = os.read(self.master, 4096)
                if not data:
                    break
                self.stream.feed(data)
        except BlockingIOError:
            # No more data available at the moment
            pass
