#!/usr/bin/env python3
"""
CryptoFile v1.0 — Criptografia e descriptografia de arquivos.
Suporta: AES-256-GCM · 3DES-CBC · RSA-2048 (híbrido)
"""

import sys
import os
from pathlib import Path

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent))

from crypto import REGISTRY
from crypto.rsa_handler import RSAHandler
from ui.terminal import (
    C, header, menu, ask, ask_password, confirm, ok, error, info, warn,
    blank, divider, section, section_end, section_row, table, press_enter,
    spinner, clear,
)
from utils.file_utils import (
    browse_file, suggest_output_path, suggest_decrypt_path,
    file_info, validate_input_file, human_size,
)

# ── Diretório padrão de chaves RSA ──────────────────────────────────
KEYS_DIR = Path.home() / '.cryptofile' / 'keys'


# ══════════════════════════════════════════════════════════════════
#   SELEÇÃO DE ALGORITMO
# ══════════════════════════════════════════════════════════════════

def select_algorithm():
    options = [
        ('1', 'AES-256-GCM',
         C.DIM + 'Simétrico · Rápido · Autenticado · Recomendado' + C.RESET),
        ('2', '3DES-CBC',
         C.DIM + 'Simétrico · Legado · HMAC-SHA256' + C.RESET),
        ('3', 'RSA-2048',
         C.DIM + 'Assimétrico · Par de chaves · Híbrido RSA+AES' + C.RESET),
        ('0', 'Voltar', ''),
    ]
    choice = menu('Selecionar Algoritmo de Criptografia', options)
    if choice == '0':
        return None
    return REGISTRY[choice]


# ══════════════════════════════════════════════════════════════════
#   FLUXO DE CRIPTOGRAFIA
# ══════════════════════════════════════════════════════════════════

def flow_encrypt():
    header()
    info('Fluxo: Criptografar Arquivo\n')

    handler = select_algorithm()
    if handler is None:
        return

    header()
    section(f'Criptografar com {handler.name}')
    section_row(f'  Tipo  : {C.CYAN}{handler.kind.capitalize()}{C.RESET}')
    section_row(f'  Chave : {C.DIM}{handler.key_info}{C.RESET}')
    section_row('')
    section_end()

    # ── Selecionar arquivo de entrada ─────────────────────────────
    src = browse_file(title='Selecionar Arquivo para Criptografar')
    if src is None:
        warn('Operação cancelada.')
        return

    finfo = file_info(src)
    blank()
    section('Arquivo Selecionado')
    section_row(f'  Nome    : {C.WHITE}{finfo["nome"]}{C.RESET}')
    section_row(f'  Caminho : {C.DIM}{finfo["caminho"]}{C.RESET}')
    section_row(f'  Tamanho : {C.CYAN}{finfo["tamanho"]}{C.RESET}')
    section_end()

    # ── Arquivo de saída ──────────────────────────────────────────
    default_dst = suggest_output_path(src)
    raw_dst = ask('Caminho do arquivo cifrado', str(default_dst))
    dst = Path(raw_dst).expanduser().resolve()

    if dst.exists():
        if not confirm(f'Arquivo {dst.name} já existe. Sobrescrever?'):
            warn('Operação cancelada.')
            return

    # ── Coleta de credenciais/chaves ──────────────────────────────
    kwargs = {}

    if handler.kind == 'simétrico':
        while True:
            pwd1 = ask_password('Senha de criptografia')
            pwd2 = ask_password('Confirmar senha')
            if pwd1 == pwd2 and pwd1:
                kwargs['password'] = pwd1
                break
            if not pwd1:
                warn('A senha não pode ser vazia.')
            else:
                warn('As senhas não conferem. Tente novamente.')

    else:  # assimétrico (RSA)
        blank()
        info('Você precisa de uma chave pública RSA (.pem).')
        info(f'Chaves padrão ficam em: {KEYS_DIR}')
        blank()

        options_key = [
            ('1', 'Usar chave pública existente'),
            ('2', 'Gerar novo par de chaves agora'),
            ('0', 'Cancelar'),
        ]
        kc = menu('Chave Pública RSA', options_key)

        if kc == '0':
            return

        if kc == '2':
            gen_rsa_keypair()

        pub_path = browse_file(title='Selecionar Chave Pública (.pem)')
        if pub_path is None:
            warn('Operação cancelada.')
            return
        kwargs['public_key_path'] = pub_path

    # ── Executa criptografia ──────────────────────────────────────
    blank()
    try:
        meta = spinner(
            f'Criptografando com {handler.name}...',
            handler.encrypt_file, src, dst, **kwargs,
        )
        blank()
        section('✔ Arquivo Criptografado com Sucesso')
        section_row(f'  Algoritmo : {C.CYAN}{meta["algorithm"]}{C.RESET}')
        section_row(f'  Destino   : {C.WHITE}{dst}{C.RESET}')
        section_row(f'  Tamanho   : {C.DIM}{human_size(dst.stat().st_size)}{C.RESET}')
        if 'salt_hex' in meta:
            section_row(f'  Salt (hex): {C.DIM}{meta["salt_hex"][:32]}…{C.RESET}')
        section_end()
    except Exception as e:
        error(f'Falha na criptografia: {e}')

    press_enter()


# ══════════════════════════════════════════════════════════════════
#   FLUXO DE DESCRIPTOGRAFIA
# ══════════════════════════════════════════════════════════════════

def _detect_handler(src: Path):
    """Tenta detectar o algoritmo pelo magic bytes do arquivo."""
    from crypto.aes_handler import AESHandler, MAGIC as AES_MAGIC
    from crypto.des_handler import DESHandler, MAGIC as DES_MAGIC
    from crypto.rsa_handler import RSAHandler, MAGIC as RSA_MAGIC

    try:
        with open(src, 'rb') as f:
            head = f.read(16)
    except Exception:
        return None

    mapping = {
        AES_MAGIC: REGISTRY['1'],
        DES_MAGIC: REGISTRY['2'],
        RSA_MAGIC: REGISTRY['3'],
    }
    for magic, handler in mapping.items():
        if head.startswith(magic):
            return handler
    return None


def flow_decrypt():
    header()
    info('Fluxo: Descriptografar Arquivo\n')

    # ── Selecionar arquivo cifrado ────────────────────────────────
    src = browse_file(title='Selecionar Arquivo Criptografado')
    if src is None:
        warn('Operação cancelada.')
        return

    # Tenta detectar algoritmo automaticamente
    handler = _detect_handler(src)
    if handler:
        info(f'Algoritmo detectado automaticamente: {C.CYAN}{handler.name}{C.RESET}')
        blank()
        if not confirm(f'Usar {handler.name} para descriptografar?'):
            handler = None

    if handler is None:
        handler = select_algorithm()
        if handler is None:
            return

    finfo = file_info(src)
    blank()
    section(f'Descriptografar com {handler.name}')
    section_row(f'  Arquivo : {C.WHITE}{finfo["nome"]}{C.RESET}')
    section_row(f'  Tamanho : {C.CYAN}{finfo["tamanho"]}{C.RESET}')
    section_end()

    # ── Arquivo de saída ──────────────────────────────────────────
    default_dst = suggest_decrypt_path(src)
    raw_dst = ask('Caminho do arquivo restaurado', str(default_dst))
    dst = Path(raw_dst).expanduser().resolve()

    if dst.exists():
        if not confirm(f'Arquivo {dst.name} já existe. Sobrescrever?'):
            warn('Operação cancelada.')
            return

    # ── Coleta de credenciais ─────────────────────────────────────
    kwargs = {}

    if handler.kind == 'simétrico':
        kwargs['password'] = ask_password('Senha de descriptografia')

    else:  # RSA
        blank()
        info('Selecione a chave privada RSA (.pem) correspondente.')
        priv_path = browse_file(title='Selecionar Chave Privada (.pem)')
        if priv_path is None:
            warn('Operação cancelada.')
            return
        kwargs['private_key_path'] = priv_path

        pp = ask_password('Senha da chave privada (deixe vazio se não houver)')
        kwargs['passphrase'] = pp

    # ── Executa descriptografia ───────────────────────────────────
    blank()
    try:
        spinner(
            f'Descriptografando com {handler.name}...',
            handler.decrypt_file, src, dst, **kwargs,
        )
        blank()
        section('✔ Arquivo Descriptografado com Sucesso')
        section_row(f'  Destino : {C.WHITE}{dst}{C.RESET}')
        section_row(f'  Tamanho : {C.CYAN}{human_size(dst.stat().st_size)}{C.RESET}')
        section_end()
    except Exception as e:
        error(f'Falha na descriptografia: {e}')
        info('Verifique se a senha/chave está correta e o arquivo não está corrompido.')

    press_enter()


# ══════════════════════════════════════════════════════════════════
#   GERENCIAR CHAVES RSA
# ══════════════════════════════════════════════════════════════════

def gen_rsa_keypair():
    header()
    section('Gerar Par de Chaves RSA-2048')
    section_row(f'  Diretório padrão: {C.DIM}{KEYS_DIR}{C.RESET}')
    section_end()

    name = ask('Nome para as chaves (ex: meu_perfil)', 'minhas_chaves')
    priv = Path(ask('Salvar chave privada em', str(KEYS_DIR / f'{name}_private.pem')))
    pub  = Path(ask('Salvar chave pública em',  str(KEYS_DIR / f'{name}_public.pem')))

    blank()
    pp = ask_password('Senha para proteger a chave privada (opcional, ENTER para nenhuma)')
    blank()

    try:
        spinner(
            'Gerando par de chaves RSA-2048…',
            RSAHandler.generate_keypair, priv, pub, pp,
        )
        blank()
        section('✔ Par de Chaves Gerado')
        section_row(f'  Privada : {C.WHITE}{priv}{C.RESET}')
        section_row(f'  Pública : {C.WHITE}{pub}{C.RESET}')
        section_row('')
        section_row(C.YELLOW + '  ⚠  Guarde a chave privada em local seguro!' + C.RESET)
        section_row(C.YELLOW + '     Sem ela não é possível descriptografar os arquivos.' + C.RESET)
        section_end()
    except Exception as e:
        error(f'Erro ao gerar chaves: {e}')

    press_enter()


def list_rsa_keys():
    header()
    section('Chaves RSA Disponíveis')

    pems = []
    if KEYS_DIR.exists():
        pems = sorted(KEYS_DIR.glob('*.pem'))

    if not pems:
        section_row(f'  {C.DIM}Nenhuma chave encontrada em {KEYS_DIR}{C.RESET}')
    else:
        for p in pems:
            section_row(f'  {C.GREEN}•{C.RESET}  {p.name}  {C.DIM}({human_size(p.stat().st_size)}){C.RESET}')

    section_end()
    press_enter()


def manage_keys():
    while True:
        header()
        choice = menu('Gerenciar Chaves RSA', [
            ('1', 'Gerar novo par de chaves RSA-2048'),
            ('2', 'Listar chaves existentes'),
            ('0', 'Voltar ao menu principal'),
        ])
        if choice == '0':
            break
        elif choice == '1':
            gen_rsa_keypair()
        elif choice == '2':
            list_rsa_keys()


# ══════════════════════════════════════════════════════════════════
#   SOBRE OS ALGORITMOS
# ══════════════════════════════════════════════════════════════════

def show_about():
    header()
    section('Sobre os Algoritmos')

    rows = []
    for key, h in REGISTRY.items():
        tipo = (C.GREEN + '🔒 Simétrico' + C.RESET
                if h.kind == 'simétrico'
                else C.MAGENTA + '🔑 Assimétrico' + C.RESET)
        rows.append([h.name, tipo, h.description])

    section_row('')
    for h in REGISTRY.values():
        kind_color = C.GREEN if h.kind == 'simétrico' else C.MAGENTA
        section_row(f'  {C.BOLD}{C.CYAN}{h.name}{C.RESET}')
        section_row(f'    Tipo   : {kind_color}{h.kind.capitalize()}{C.RESET}')
        section_row(f'    Chave  : {C.DIM}{h.key_info}{C.RESET}')
        section_row(f'    Info   : {h.description}')
        section_row('')

    section_row(C.DIM + '  AES-256-GCM  → Padrão recomendado para uso geral.' + C.RESET)
    section_row(C.DIM + '  3DES-CBC     → Legado; use apenas para compatibilidade.' + C.RESET)
    section_row(C.DIM + '  RSA-2048     → Ideal para troca segura de chaves entre partes.' + C.RESET)
    section_end()

    press_enter()


# ══════════════════════════════════════════════════════════════════
#   MAIN LOOP
# ══════════════════════════════════════════════════════════════════

def main():
    while True:
        header()

        main_options = [
            ('1', 'Criptografar arquivo',
             C.DIM + 'Selecionar arquivo e algoritmo para cifrar' + C.RESET),
            ('2', 'Descriptografar arquivo',
             C.DIM + 'Restaurar arquivo cifrado ao original' + C.RESET),
            ('3', 'Gerenciar chaves RSA',
             C.DIM + 'Gerar / listar pares de chaves pública+privada' + C.RESET),
            ('4', 'Sobre os algoritmos',
             C.DIM + 'AES-256-GCM · 3DES-CBC · RSA-2048' + C.RESET),
            ('0', 'Sair', ''),
        ]

        choice = menu('Menu Principal', main_options)

        if choice == '0':
            clear()
            info('Até logo! 👋')
            blank()
            sys.exit(0)
        elif choice == '1':
            flow_encrypt()
        elif choice == '2':
            flow_decrypt()
        elif choice == '3':
            manage_keys()
        elif choice == '4':
            show_about()


if __name__ == '__main__':
    main()