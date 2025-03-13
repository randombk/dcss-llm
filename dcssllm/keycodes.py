from enum import Enum

class Keycode(Enum):
    # Arrow keys
    UP = b'\x1b[A'
    DOWN = b'\x1b[B'
    RIGHT = b'\x1b[C'
    LEFT = b'\x1b[D'
    
    # Navigation keys
    HOME = b'\x1b[H'
    END = b'\x1b[F'
    PAGE_UP = b'\x1b[5~'
    PAGE_DOWN = b'\x1b[6~'
    INSERT = b'\x1b[2~'
    DELETE = b'\x1b[3~'
    
    # Standard keys
    ESC = b'\x1b'
    ENTER = b'\r'
    BACKSPACE = b'\x7f'
    TAB = b'\t'
    SPACE = b' '
    
    # Function keys (common in many ttys)
    F1 = b'\x1bOP'
    F2 = b'\x1bOQ'
    F3 = b'\x1bOR'
    F4 = b'\x1bOS'
    F5 = b'\x1bOT'
    F6 = b'\x1bOU'
    F7 = b'\x1bOV'
    F8 = b'\x1bOW'
    F9 = b'\x1bOX'
    F10 = b'\x1bOY'
    F11 = b'\x1bOZ'
    
    # Control keys (Ctrl-A to Ctrl-Z)
    CTRL_A = b'\x01'
    CTRL_B = b'\x02'
    CTRL_C = b'\x03'
    CTRL_D = b'\x04'
    CTRL_E = b'\x05'
    CTRL_F = b'\x06'
    CTRL_G = b'\x07'
    CTRL_H = b'\x08'
    CTRL_I = b'\x09'
    CTRL_J = b'\x0a'
    CTRL_K = b'\x0b'
    CTRL_L = b'\x0c'
    CTRL_M = b'\x0d'
    CTRL_N = b'\x0e'
    CTRL_O = b'\x0f'
    CTRL_P = b'\x10'
    CTRL_Q = b'\x11'
    CTRL_R = b'\x12'
    CTRL_S = b'\x13'
    CTRL_T = b'\x14'
    CTRL_U = b'\x15'
    CTRL_V = b'\x16'
    CTRL_W = b'\x17'
    CTRL_X = b'\x18'
    CTRL_Y = b'\x19'
    CTRL_Z = b'\x1a'