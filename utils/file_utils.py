"""
Utilitários de arquivo: navegação de diretórios, seleção interativa, info.
"""
from pathlib import Path
from ui.terminal import C, ask, warn, section, section_end, section_row


# ─────────────────────────── INFO ──────────────────────────────────

def human_size(n: float) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{n:.1f} {unit}' if unit != 'B' else f'{n} B'
        n /= 1024
    return f'{n:.1f} PB'


def file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        'nome'    : path.name,
        'caminho' : str(path.resolve()),
        'tamanho' : human_size(stat.st_size),
        'bytes'   : stat.st_size,
    }


# ─────────────────────────── BROWSER ───────────────────────────────

def _list_dir(directory: Path) -> tuple[list[Path], list[Path]]:
    """Retorna (subpastas, arquivos) ordenados."""
    try:
        entries = sorted(directory.iterdir())
    except PermissionError:
        return [], []
    dirs  = [e for e in entries if e.is_dir()  and not e.name.startswith('.')]
    files = [e for e in entries if e.is_file() and not e.name.startswith('.')]
    return dirs, files


def browse_file(start_dir: Path | None = None, title: str = 'Selecionar Arquivo') -> Path | None:
    """
    Navegador interativo de arquivos no terminal.
    Retorna o Path do arquivo selecionado ou None se o usuário cancelar.
    """
    cwd = (start_dir or Path.cwd()).resolve()

    while True:
        dirs, files = _list_dir(cwd)
        section(title)
        section_row(C.DIM + f'  📁  {cwd}' + C.RESET)

        # Opção de subir um nível
        idx = 0
        section_row('')
        section_row(f'  {C.YELLOW}[0]{C.RESET}  {C.DIM}↑  Subir um nível{C.RESET}')
        section_row(f'  {C.YELLOW}[P]{C.RESET}  {C.DIM}✎  Digitar caminho manualmente{C.RESET}')
        section_row(f'  {C.YELLOW}[C]{C.RESET}  {C.DIM}✘  Cancelar{C.RESET}')

        # Diretórios
        dir_indices = {}
        if dirs:
            section_row('')
            section_row(C.BOLD + '  Pastas:' + C.RESET)
            for d in dirs:
                idx += 1
                dir_indices[str(idx)] = d
                section_row(f'  {C.CYAN}[{idx:2}]{C.RESET}  📁  {d.name}/')

        # Arquivos
        file_indices = {}
        if files:
            section_row('')
            section_row(C.BOLD + '  Arquivos:' + C.RESET)
            for f in files:
                idx += 1
                file_indices[str(idx)] = f
                size = human_size(f.stat().st_size)
                section_row(
                    f'  {C.GREEN}[{idx:2}]{C.RESET}  📄  '
                    f'{C.WHITE}{f.name}{C.RESET}  '
                    f'{C.DIM}({size}){C.RESET}'
                )

        section_row('')
        section_end()

        valid = {'0', 'p', 'c'} | set(dir_indices) | set(file_indices)
        choice = input(C.CYAN + '  → Escolha: ' + C.RESET).strip().lower()

        if choice == 'c':
            return None

        if choice == '0':
            cwd = cwd.parent
            continue

        if choice == 'p':
            raw = ask('Caminho completo do arquivo')
            p   = Path(raw).expanduser().resolve()
            if p.is_file():
                return p
            warn('Arquivo não encontrado. Tente novamente.')
            continue

        if choice in dir_indices:
            cwd = dir_indices[choice]
            continue

        if choice in file_indices:
            return file_indices[choice]

        warn('Opção inválida.')


def suggest_output_path(src: Path, suffix: str = '.enc') -> Path:
    """Sugere caminho de saída: mesmo diretório, mesmo nome + sufixo."""
    return src.parent / (src.name + suffix)


def suggest_decrypt_path(src: Path) -> Path:
    """Remove sufixo .enc se existir, senão adiciona .dec."""
    name = src.name
    if name.endswith('.enc'):
        new_name = name[:-4]
    else:
        new_name = name + '.dec'
    return src.parent / new_name


def validate_input_file(path_str: str) -> Path | None:
    p = Path(path_str).expanduser().resolve()
    if not p.exists():
        warn(f'Arquivo não encontrado: {p}')
        return None
    if not p.is_file():
        warn('O caminho informado não é um arquivo.')
        return None
    return p