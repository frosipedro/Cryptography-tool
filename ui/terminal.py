"""
Terminal UI — caixas, cores, menus e feedback visual com ANSI.
"""
import os
import re
import sys
import time
import getpass

# ─────────────────────────── ANSI CODES ────────────────────────────

class C:
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN    = '\033[96m'
    WHITE   = '\033[97m'
    GRAY    = '\033[90m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    UL      = '\033[4m'
    RESET   = '\033[0m'

W = 72  # largura total da caixa

# ─────────────────────────── HELPERS ───────────────────────────────

def _strip(s: str) -> str:
    """Remove códigos ANSI para medir comprimento visível."""
    return re.sub(r'\033\[[^m]*m', '', s)

def _pad(content: str, width: int) -> str:
    """Padding baseado no comprimento visível (ignora ANSI)."""
    visible = len(_strip(content))
    return content + ' ' * max(0, width - visible)

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

# ─────────────────────────── BOX DRAWING ───────────────────────────

def _top(color=C.CYAN):
    print(color + '╔' + '═' * (W - 2) + '╗' + C.RESET)

def _bot(color=C.CYAN):
    print(color + '╚' + '═' * (W - 2) + '╝' + C.RESET)

def _sep(color=C.CYAN):
    print(color + '╠' + '═' * (W - 2) + '╣' + C.RESET)

def _row(content: str = '', color=C.CYAN):
    inner = W - 4  # "║ " + content + " ║"
    padded = _pad(content, inner)
    print(color + '║ ' + C.RESET + padded + color + ' ║' + C.RESET)

def _blank(color=C.CYAN):
    _row('', color)

# ─────────────────────────── COMPONENTES ───────────────────────────

def header():
    clear()
    title  = C.BOLD + C.CYAN + '🔐  CryptoFile  v1.0' + C.RESET
    sub    = C.DIM + 'Criptografia de arquivos com AES-256 · 3DES · RSA-2048' + C.RESET
    _top()
    _row(_pad(title, W - 4))
    _row(_pad(sub,   W - 4))
    _bot()
    print()

def section(title: str):
    label = C.BOLD + C.CYAN + title + C.RESET
    _top()
    _row(label)
    _sep()

def section_end():
    _bot()
    print()

def section_row(content: str):
    _row(content)

def info(msg: str):
    print(C.CYAN  + '  ℹ  ' + C.RESET + msg)

def ok(msg: str):
    print(C.GREEN + '  ✔  ' + C.RESET + msg)

def warn(msg: str):
    print(C.YELLOW + '  ⚠  ' + C.RESET + msg)

def error(msg: str):
    print(C.RED + '  ✘  ' + C.RESET + msg)

def divider():
    print(C.DIM + '  ' + '─' * (W - 4) + C.RESET)

def blank():
    print()

# ─────────────────────────── MENUS ─────────────────────────────────

def menu(title: str, options: list[tuple]) -> str:
    """
    Exibe um menu e retorna a chave escolhida.
    options: [(key, label, description?), ...]
    """
    section(title)
    for item in options:
        key, label = item[0], item[1]
        desc = item[2] if len(item) > 2 else ''
        key_fmt  = C.BOLD + C.YELLOW + f'[{key}]' + C.RESET
        label_fmt = C.WHITE + label + C.RESET
        desc_fmt  = C.DIM + f'  {desc}' + C.RESET if desc else ''
        _row(f'  {key_fmt}  {label_fmt}{desc_fmt}')
    _blank()
    _bot()
    print()
    keys = [str(o[0]) for o in options]
    while True:
        val = input(C.CYAN + '  → ' + C.RESET + 'Escolha: ').strip()
        if val in keys:
            return val
        warn(f'Opção inválida. Escolha entre: {", ".join(keys)}')

def ask(prompt: str, default: str = '') -> str:
    hint = f' [{C.DIM}{default}{C.RESET}]' if default else ''
    val = input(C.CYAN + f'  → {prompt}{hint}: ' + C.RESET).strip()
    return val or default

def ask_password(prompt: str = 'Senha/Chave') -> str:
    return getpass.getpass(C.CYAN + f'  → {prompt}: ' + C.RESET)

def confirm(prompt: str) -> bool:
    val = input(C.CYAN + f'  → {prompt} [s/N]: ' + C.RESET).strip().lower()
    return val in ('s', 'sim', 'y', 'yes')

# ─────────────────────────── PROGRESS ──────────────────────────────

def progress(label: str, iterable=None, total: int = 30):
    """Barra de progresso simples para operações sem iterável."""
    sys.stdout.write(f'\n  {label}\n  [')
    for i in range(total):
        sys.stdout.write(C.GREEN + '█' + C.RESET)
        sys.stdout.flush()
        time.sleep(0.015)
    sys.stdout.write(']\n\n')

def spinner(label: str, func, *args, **kwargs):
    """Executa func enquanto exibe um spinner."""
    frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    result: list = [None]
    exc: list = [None]
    done   = [False]

    import threading
    def worker():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exc[0] = e
        finally:
            done[0] = True

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    i = 0
    while not done[0]:
        sys.stdout.write(f'\r  {C.CYAN}{frames[i % len(frames)]}{C.RESET}  {label}   ')
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write('\r' + ' ' * 60 + '\r')
    sys.stdout.flush()
    t.join()

    if exc[0]:
        raise exc[0]
    return result[0]

# ─────────────────────────── TABELA ────────────────────────────────

def table(headers: list[str], rows: list[list[str]], col_colors: list | None = None):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(_strip(str(cell))))

    def fmt_row(cells, colors=None, bold=False):
        parts = []
        for i, cell in enumerate(cells):
            cc = (colors[i] if colors and i < len(colors) else '') if colors else ''
            b  = C.BOLD if bold else ''
            s  = f'{b}{cc}{_pad(str(cell), widths[i])}{C.RESET}'
            parts.append(s)
        return '  ' + C.DIM + '│' + C.RESET + f'  {C.DIM}│{C.RESET}  '.join(parts) + '  ' + C.DIM + '│' + C.RESET

    sep = '  ' + C.DIM + '┼'.join(['─' * (w + 4) for w in widths]) + C.RESET
    top = '  ' + C.DIM + '┬'.join(['─' * (w + 4) for w in widths]) + C.RESET
    bot = '  ' + C.DIM + '┴'.join(['─' * (w + 4) for w in widths]) + C.RESET

    print(top)
    print(fmt_row(headers, bold=True))
    print(sep)
    for row in rows:
        print(fmt_row(row, col_colors))
    print(bot)
    print()

def press_enter():
    input(C.DIM + '\n  Pressione ENTER para continuar...' + C.RESET)