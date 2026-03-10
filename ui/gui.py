"""
GUI — Interface gráfica com customtkinter para o CryptoFile v1.0.
Design: Material Design 3 / Dark Mode moderno.

Dependência extra:  pip install customtkinter
"""
import sys
import tkinter as tk
import threading
from typing import Any
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto import REGISTRY
from crypto.aes_handler import MAGIC as AES_MAGIC
from crypto.des_handler import MAGIC as DES_MAGIC
from crypto.rsa_handler import RSAHandler, MAGIC as RSA_MAGIC

KEYS_DIR = Path.home() / '.cryptofile' / 'keys'

# ── Paleta Material Design 3 – Dark Surface ─────────────────────────
BG        = '#0d1117'   # background principal
SURF      = '#161b22'   # surface (header, cards)
SURF2     = '#1c2128'   # surface raised
SURF3     = '#21262d'   # surface mais elevada
BORDER    = '#30363d'   # bordas sutis
ACCENT    = '#388bfd'   # primary / azul M3
ACCENT_H  = '#1f6feb'   # primary hover
ACCENT_DIM = '#1a3a6e'  # primary desabilitado
GREEN     = '#3fb950'
RED       = '#f85149'
YELLOW    = '#d29922'
PURPLE    = '#bc8cff'
TEXT      = '#e6edf3'
DIM       = '#7d8590'

# ── Config global CTk ────────────────────────────────────────────────
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')

# ── Fontes ───────────────────────────────────────────────────────────
FONT_TITLE  = ('Segoe UI', 20, 'bold')
FONT_LABEL  = ('Segoe UI', 12)
FONT_SMALL  = ('Segoe UI', 11)
FONT_MONO   = ('Consolas', 10)
FONT_SECTION = ('Segoe UI', 11, 'bold')
FONT_BTN_PRIMARY = ('Segoe UI', 13, 'bold')
FONT_BTN    = ('Segoe UI', 12)


# ════════════════════════════════════════════════════════════════════
#   COMPONENTES REUTILIZÁVEIS
# ════════════════════════════════════════════════════════════════════

class Card(ctk.CTkFrame):
    """Cartão com título de seção estilo Material 3."""

    def __init__(self, parent, title: str = '', **kwargs):
        kwargs.setdefault('fg_color', SURF2)
        kwargs.setdefault('corner_radius', 12)
        kwargs.setdefault('border_width', 1)
        kwargs.setdefault('border_color', BORDER)
        super().__init__(parent, **kwargs)

        if title:
            ctk.CTkLabel(
                self, text=title,
                font=ctk.CTkFont(*FONT_SECTION),
                text_color=ACCENT,
                anchor='w',
            ).pack(anchor='w', padx=16, pady=(12, 0))

        self.inner = ctk.CTkFrame(self, fg_color='transparent')
        self.inner.pack(fill='both', expand=True, padx=16, pady=(8, 14))


def _make_entry(parent, var=None, show: str | None = None, height: int = 34, **kwargs) -> ctk.CTkEntry:
    kw: dict[str, Any] = dict(
        textvariable=var,
        fg_color=SURF3,
        border_color=BORDER,
        border_width=1,
        text_color=TEXT,
        height=height,
        corner_radius=8,
        font=ctk.CTkFont(*FONT_SMALL),
    )
    if show:
        kw['show'] = show
    kw.update(kwargs)
    return ctk.CTkEntry(parent, **kw)  # type: ignore[arg-type]


def _make_btn(parent, text, cmd, primary=False, height=34, width=None, **kwargs) -> ctk.CTkButton:
    kw = dict(
        text=text,
        command=cmd,
        height=height,
        corner_radius=8,
        font=ctk.CTkFont(*FONT_BTN_PRIMARY) if primary else ctk.CTkFont(*FONT_BTN),
        fg_color=ACCENT if primary else SURF3,
        hover_color=ACCENT_H if primary else BORDER,
        text_color=TEXT,
        border_width=0 if primary else 1,
        border_color=BORDER,
    )
    if width:
        kw['width'] = width
    kw.update(kwargs)
    return ctk.CTkButton(parent, **kw)  # type: ignore[arg-type]


def _file_row(parent, var: ctk.StringVar, btn_label: str, cmd):
    """Linha de entry + botão de arquivo."""
    row = ctk.CTkFrame(parent, fg_color='transparent')
    row.pack(fill='x')
    entry = _make_entry(row, var=var)
    entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
    _make_btn(row, btn_label, cmd, width=110).pack(side='left')


def _label_row(parent, label: str, widget_factory, pady=3):
    """Linha label + widget alinhados."""
    row = ctk.CTkFrame(parent, fg_color='transparent')
    row.pack(fill='x', pady=pady)
    ctk.CTkLabel(
        row, text=label, text_color=DIM,
        font=ctk.CTkFont(*FONT_LABEL),
        anchor='w', width=180,
    ).pack(side='left')
    w = widget_factory(row)
    w.pack(side='left', fill='x', expand=True)
    return row, w


# ════════════════════════════════════════════════════════════════════
#   JANELA PRINCIPAL
# ════════════════════════════════════════════════════════════════════

class CryptoFileGUI:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title('CryptoFile v1.0')
        self.root.geometry('1000x860')
        self.root.minsize(700, 620)
        self.root.configure(fg_color=BG)

        self._busy = False
        self._anim_id = None
        self._anim_val = 0.0

        self._build_ui()

    # ────────────────────────────────────────────────────────────────
    #   LAYOUT PRINCIPAL
    # ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_tabs()
        self._build_statusbar()
        self._build_log()

    def _build_header(self):
        hdr = ctk.CTkFrame(self.root, fg_color=SURF, corner_radius=0, height=72)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)

        # Lado esquerdo: ícone + nome + versão
        left = ctk.CTkFrame(hdr, fg_color='transparent')
        left.place(relx=0, rely=0.5, anchor='w', x=24)

        icon_bg = ctk.CTkFrame(left, fg_color=ACCENT_DIM, corner_radius=10,
                               width=40, height=40)
        icon_bg.pack(side='left', padx=(0, 14))
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text='🔐', font=ctk.CTkFont(size=18)).place(relx=.5, rely=.5, anchor='center')

        text_col = ctk.CTkFrame(left, fg_color='transparent')
        text_col.pack(side='left')

        name_row = ctk.CTkFrame(text_col, fg_color='transparent')
        name_row.pack(anchor='w')
        ctk.CTkLabel(name_row, text='CryptoFile',
                     font=ctk.CTkFont('Segoe UI', 18, 'bold'),
                     text_color=TEXT).pack(side='left')
        ctk.CTkLabel(name_row, text=' v1.0',
                     font=ctk.CTkFont('Segoe UI', 13),
                     text_color=ACCENT).pack(side='left', pady=(2, 0))

        ctk.CTkLabel(text_col,
                     text='Criptografia de arquivos  ·  AES-256-GCM  ·  3DES-CBC  ·  RSA-2048',
                     font=ctk.CTkFont('Segoe UI', 10),
                     text_color=DIM).pack(anchor='w', pady=(1, 0))

        # Badges à direita
        right = ctk.CTkFrame(hdr, fg_color='transparent')
        right.place(relx=1, rely=0.5, anchor='e', x=-24)
        for badge in ('AES-256', '3DES', 'RSA'):
            f = ctk.CTkFrame(right, fg_color=SURF3, corner_radius=6,
                             border_width=1, border_color=BORDER)
            f.pack(side='left', padx=3)
            ctk.CTkLabel(f, text=badge,
                         font=ctk.CTkFont('Consolas', 10, 'bold'),
                         text_color=DIM).pack(padx=8, pady=4)

    def _build_tabs(self):
        self.nb = ctk.CTkTabview(
            self.root,
            fg_color=BG,
            segmented_button_fg_color=SURF,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_H,
            segmented_button_unselected_color=SURF,
            segmented_button_unselected_hover_color=SURF2,
            text_color=TEXT,
            text_color_disabled=DIM,
            corner_radius=0,
            anchor='nw',
        )
        self.nb.pack(fill='both', expand=True, padx=0, pady=0)
        self.nb._segmented_button.configure(font=ctk.CTkFont('Segoe UI', 12))

        self._build_encrypt_tab()
        self._build_decrypt_tab()
        self._build_keys_tab()
        self._build_about_tab()

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self.root, fg_color=SURF, corner_radius=0, height=6)
        bar.pack(fill='x')
        bar.pack_propagate(False)

        self._progress = ctk.CTkProgressBar(
            bar,
            fg_color=SURF2,
            progress_color=ACCENT,
            height=6,
            corner_radius=0,
            mode='determinate',
        )
        self._progress.pack(fill='x')
        self._progress.set(0)

    def _build_log(self):
        log_outer = ctk.CTkFrame(self.root, fg_color=SURF, corner_radius=0)
        log_outer.pack(fill='x')

        hdr_row = ctk.CTkFrame(log_outer, fg_color='transparent')
        hdr_row.pack(fill='x', padx=16, pady=(8, 4))
        ctk.CTkLabel(hdr_row, text='LOG DE OPERAÇÕES',
                     font=ctk.CTkFont('Segoe UI', 9, 'bold'),
                     text_color=DIM).pack(side='left')

        # tk.Text para suporte a tags coloridas dentro de um frame ctk
        log_wrap = ctk.CTkFrame(log_outer, fg_color=SURF3, corner_radius=8,
                                border_width=1, border_color=BORDER)
        log_wrap.pack(fill='x', padx=12, pady=(0, 12))

        self._log_text = tk.Text(
            log_wrap, height=5,
            bg=SURF3, fg=TEXT,
            insertbackground=TEXT,
            font=FONT_MONO,
            relief='flat', bd=10,
            state='disabled', wrap='word',
            selectbackground=ACCENT, selectforeground=BG,
        )
        sb = tk.Scrollbar(log_wrap, command=self._log_text.yview,
                          bg=SURF3, troughcolor=SURF3,
                          activebackground=DIM, relief='flat', bd=0)
        self._log_text.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self._log_text.pack(side='left', fill='x', expand=True)

        self._log_text.tag_configure('ok',   foreground=GREEN)
        self._log_text.tag_configure('err',  foreground=RED)
        self._log_text.tag_configure('info', foreground=ACCENT)
        self._log_text.tag_configure('warn', foreground=YELLOW)

    # ────────────────────────────────────────────────────────────────
    #   ABA: CRIPTOGRAFAR
    # ────────────────────────────────────────────────────────────────

    def _build_encrypt_tab(self):
        self.nb.add('  Criptografar  ')
        frame = self.nb.tab('  Criptografar  ')
        self._add_scroll_frame(frame, self._fill_encrypt_tab)

    def _fill_encrypt_tab(self, parent):
        # Algoritmo
        alg_card = Card(parent, 'Algoritmo')
        alg_card.pack(fill='x', padx=4, pady=(0, 10))

        self._enc_algo = ctk.StringVar(value='1')
        algo_row = ctk.CTkFrame(alg_card.inner, fg_color='transparent')
        algo_row.pack(fill='x')

        for key, h in REGISTRY.items():
            ctk.CTkRadioButton(
                algo_row,
                text=f'  {h.name}  —  {h.kind}',
                variable=self._enc_algo, value=key,
                command=self._on_enc_algo_change,
                font=ctk.CTkFont(*FONT_LABEL),
                text_color=TEXT, fg_color=ACCENT,
                hover_color=ACCENT_H, border_color=BORDER,
            ).pack(side='left', padx=(0, 24), pady=2)

        # Entrada
        in_card = Card(parent, 'Arquivo de Entrada')
        in_card.pack(fill='x', padx=4, pady=(0, 10))
        self._enc_src = ctk.StringVar()
        _file_row(in_card.inner, self._enc_src, 'Procurar…', self._browse_enc_src)

        # Saída
        out_card = Card(parent, 'Arquivo de Saída')
        out_card.pack(fill='x', padx=4, pady=(0, 10))
        self._enc_dst = ctk.StringVar()
        _file_row(out_card.inner, self._enc_dst, 'Salvar como…', self._browse_enc_dst)

        # Credenciais
        self._enc_cred_card = Card(parent, 'Chave / Senha')
        self._enc_cred_card.pack(fill='x', padx=4, pady=(0, 10))
        self._enc_cred_widgets: dict = {}
        self._build_enc_sym_creds()

        # Botão
        _make_btn(parent, '🔒   Criptografar', self._run_encrypt,
                  primary=True, height=44).pack(
            side='right', padx=4, pady=(0, 4))

    def _build_enc_sym_creds(self):
        for w in self._enc_cred_card.inner.winfo_children():
            w.destroy()
        self._enc_cred_widgets.clear()
        for label, key in [('Senha:', 'pwd1'), ('Confirmar senha:', 'pwd2')]:
            _, e = _label_row(
                self._enc_cred_card.inner, label,
                lambda p, k=key: _make_entry(p, show='•'))
            self._enc_cred_widgets[key] = e

    def _build_enc_rsa_creds(self):
        for w in self._enc_cred_card.inner.winfo_children():
            w.destroy()
        self._enc_cred_widgets.clear()
        var = ctk.StringVar()
        row = ctk.CTkFrame(self._enc_cred_card.inner, fg_color='transparent')
        row.pack(fill='x', pady=3)
        ctk.CTkLabel(row, text='Chave pública (.pem):', text_color=DIM,
                     font=ctk.CTkFont(*FONT_LABEL), anchor='w', width=180).pack(side='left')
        _make_entry(row, var=var).pack(side='left', fill='x', expand=True, padx=(0, 8))
        _make_btn(row, 'Procurar…', self._browse_enc_pub_key, width=110).pack(side='left')
        self._enc_cred_widgets['pub_key'] = var

    def _on_enc_algo_change(self):
        h = REGISTRY[self._enc_algo.get()]
        if h.kind == 'simétrico':
            self._build_enc_sym_creds()
        else:
            self._build_enc_rsa_creds()

    def _browse_enc_src(self):
        p = filedialog.askopenfilename(title='Selecionar Arquivo para Criptografar')
        if p:
            self._enc_src.set(p)
            if not self._enc_dst.get():
                self._enc_dst.set(str(_suggest_enc_path(Path(p))))

    def _browse_enc_dst(self):
        p = filedialog.asksaveasfilename(
            title='Salvar Arquivo Criptografado',
            defaultextension='.enc',
            filetypes=[('Arquivo cifrado', '*.enc'), ('Todos os arquivos', '*.*')],
        )
        if p:
            self._enc_dst.set(p)

    def _browse_enc_pub_key(self):
        p = filedialog.askopenfilename(
            title='Selecionar Chave Pública RSA',
            filetypes=[('PEM', '*.pem'), ('Todos os arquivos', '*.*')],
            initialdir=str(KEYS_DIR) if KEYS_DIR.exists() else None,
        )
        if p:
            self._enc_cred_widgets['pub_key'].set(p)

    def _run_encrypt(self):
        src = self._enc_src.get().strip()
        dst = self._enc_dst.get().strip()
        handler = REGISTRY[self._enc_algo.get()]

        if not src:
            self._log('Selecione um arquivo de entrada.', 'warn'); return
        if not dst:
            self._log('Informe o caminho do arquivo de saída.', 'warn'); return

        src_path, dst_path = Path(src), Path(dst)
        if not src_path.is_file():
            self._log(f'Arquivo não encontrado: {src}', 'err'); return

        kwargs = {}
        if handler.kind == 'simétrico':
            pwd1 = self._enc_cred_widgets['pwd1'].get()
            pwd2 = self._enc_cred_widgets['pwd2'].get()
            if not pwd1:
                self._log('A senha não pode ser vazia.', 'warn'); return
            if pwd1 != pwd2:
                self._log('As senhas não conferem.', 'warn'); return
            kwargs['password'] = pwd1
        else:
            pub = self._enc_cred_widgets['pub_key'].get().strip()
            if not pub:
                self._log('Selecione a chave pública RSA.', 'warn'); return
            kwargs['public_key_path'] = Path(pub)

        self._log(f'Criptografando {src_path.name} com {handler.name}…', 'info')
        self._set_busy(True)

        def task():
            try:
                handler.encrypt_file(src_path, dst_path, **kwargs)
                size = _human_size(dst_path.stat().st_size)
                self._log(f'Concluído → {dst_path.name}  ({size})', 'ok')
            except Exception as exc:
                self._log(f'Erro: {exc}', 'err')
            finally:
                self._set_busy(False)

        threading.Thread(target=task, daemon=True).start()

    # ────────────────────────────────────────────────────────────────
    #   ABA: DESCRIPTOGRAFAR
    # ────────────────────────────────────────────────────────────────

    def _build_decrypt_tab(self):
        self.nb.add('  Descriptografar  ')
        frame = self.nb.tab('  Descriptografar  ')
        self._add_scroll_frame(frame, self._fill_decrypt_tab)

    def _fill_decrypt_tab(self, parent):
        # Arquivo de entrada
        in_card = Card(parent, 'Arquivo Criptografado')
        in_card.pack(fill='x', padx=4, pady=(0, 10))
        self._dec_src = ctk.StringVar()
        _file_row(in_card.inner, self._dec_src, 'Procurar…', self._browse_dec_src)

        # Algoritmo
        alg_card = Card(parent, 'Algoritmo')
        alg_card.pack(fill='x', padx=4, pady=(0, 10))

        self._dec_auto = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            alg_card.inner,
            text='Detectar automaticamente',
            variable=self._dec_auto,
            command=self._on_dec_auto_change,
            font=ctk.CTkFont(*FONT_LABEL),
            text_color=TEXT, fg_color=ACCENT,
            hover_color=ACCENT_H, border_color=BORDER,
            checkmark_color=BG,
        ).pack(anchor='w', pady=(0, 8))

        self._dec_algo_row = ctk.CTkFrame(alg_card.inner, fg_color='transparent')
        self._dec_algo_row.pack(fill='x')
        self._dec_algo = ctk.StringVar(value='1')
        self._dec_radios = []
        for key, h in REGISTRY.items():
            rb = ctk.CTkRadioButton(
                self._dec_algo_row,
                text=f'  {h.name}',
                variable=self._dec_algo, value=key,
                command=self._on_dec_algo_change,
                font=ctk.CTkFont(*FONT_LABEL),
                text_color=TEXT, fg_color=ACCENT,
                hover_color=ACCENT_H, border_color=BORDER,
            )
            rb.pack(side='left', padx=(0, 24))
            self._dec_radios.append(rb)
        self._on_dec_auto_change()

        # Arquivo de saída
        out_card = Card(parent, 'Arquivo de Saída (Restaurado)')
        out_card.pack(fill='x', padx=4, pady=(0, 10))
        self._dec_dst = ctk.StringVar()
        _file_row(out_card.inner, self._dec_dst, 'Salvar como…', self._browse_dec_dst)

        # Credenciais
        self._dec_cred_card = Card(parent, 'Chave / Senha')
        self._dec_cred_card.pack(fill='x', padx=4, pady=(0, 10))
        self._dec_cred_widgets: dict = {}
        self._build_dec_sym_creds()

        # Botão
        _make_btn(parent, '🔓   Descriptografar', self._run_decrypt,
                  primary=True, height=44).pack(
            side='right', padx=4, pady=(0, 4))

    def _build_dec_sym_creds(self):
        for w in self._dec_cred_card.inner.winfo_children():
            w.destroy()
        self._dec_cred_widgets.clear()
        _, e = _label_row(
            self._dec_cred_card.inner, 'Senha:',
            lambda p: _make_entry(p, show='•'))
        self._dec_cred_widgets['pwd'] = e

    def _build_dec_rsa_creds(self):
        for w in self._dec_cred_card.inner.winfo_children():
            w.destroy()
        self._dec_cred_widgets.clear()

        # chave privada
        var_priv = ctk.StringVar()
        row = ctk.CTkFrame(self._dec_cred_card.inner, fg_color='transparent')
        row.pack(fill='x', pady=3)
        ctk.CTkLabel(row, text='Chave privada (.pem):', text_color=DIM,
                     font=ctk.CTkFont(*FONT_LABEL), anchor='w', width=200).pack(side='left')
        _make_entry(row, var=var_priv).pack(side='left', fill='x', expand=True, padx=(0, 8))
        _make_btn(row, 'Procurar…', self._browse_dec_priv_key, width=110).pack(side='left')
        self._dec_cred_widgets['priv_key'] = var_priv

        # passphrase
        var_pp = ctk.StringVar()
        _, e_pp = _label_row(
            self._dec_cred_card.inner, 'Senha da chave (opcional):',
            lambda p: _make_entry(p, var=var_pp, show='•'))
        self._dec_cred_widgets['passphrase'] = var_pp

    def _on_dec_auto_change(self):
        state = 'disabled' if self._dec_auto.get() else 'normal'
        for rb in self._dec_radios:
            rb.configure(state=state)

    def _on_dec_algo_change(self):
        h = REGISTRY[self._dec_algo.get()]
        if h.kind == 'simétrico':
            self._build_dec_sym_creds()
        else:
            self._build_dec_rsa_creds()

    def _browse_dec_src(self):
        p = filedialog.askopenfilename(
            title='Selecionar Arquivo Criptografado',
            filetypes=[('Arquivo cifrado', '*.enc'), ('Todos os arquivos', '*.*')],
        )
        if not p:
            return
        self._dec_src.set(p)
        if not self._dec_dst.get():
            self._dec_dst.set(str(_suggest_dec_path(Path(p))))
        if self._dec_auto.get():
            h = _detect_handler(Path(p))
            if h:
                self._log(f'Algoritmo detectado automaticamente: {h.name}', 'info')
                for k, v in REGISTRY.items():
                    if v is h:
                        self._dec_algo.set(k)
                        self._on_dec_algo_change()
                        break
            else:
                self._log('Não foi possível detectar o algoritmo automaticamente.', 'warn')

    def _browse_dec_dst(self):
        p = filedialog.asksaveasfilename(title='Salvar Arquivo Restaurado')
        if p:
            self._dec_dst.set(p)

    def _browse_dec_priv_key(self):
        p = filedialog.askopenfilename(
            title='Selecionar Chave Privada RSA',
            filetypes=[('PEM', '*.pem'), ('Todos os arquivos', '*.*')],
            initialdir=str(KEYS_DIR) if KEYS_DIR.exists() else None,
        )
        if p:
            self._dec_cred_widgets['priv_key'].set(p)

    def _run_decrypt(self):
        src = self._dec_src.get().strip()
        dst = self._dec_dst.get().strip()

        if not src:
            self._log('Selecione um arquivo criptografado.', 'warn'); return
        if not dst:
            self._log('Informe o caminho do arquivo de saída.', 'warn'); return

        src_path, dst_path = Path(src), Path(dst)
        if not src_path.is_file():
            self._log(f'Arquivo não encontrado: {src}', 'err'); return

        if self._dec_auto.get():
            handler = _detect_handler(src_path)
            if handler is None:
                self._log(
                    'Algoritmo não detectado. Desmarque "Detectar automaticamente" '
                    'e selecione o algoritmo manualmente.', 'warn')
                return
        else:
            handler = REGISTRY[self._dec_algo.get()]

        kwargs = {}
        if handler.kind == 'simétrico':
            pwd = self._dec_cred_widgets['pwd'].get()
            if not pwd:
                self._log('A senha não pode ser vazia.', 'warn'); return
            kwargs['password'] = pwd
        else:
            priv = self._dec_cred_widgets['priv_key'].get().strip()
            if not priv:
                self._log('Selecione a chave privada RSA.', 'warn'); return
            kwargs['private_key_path'] = Path(priv)
            kwargs['passphrase'] = self._dec_cred_widgets['passphrase'].get()

        self._log(f'Descriptografando {src_path.name} com {handler.name}…', 'info')
        self._set_busy(True)

        def task():
            try:
                handler.decrypt_file(src_path, dst_path, **kwargs)
                size = _human_size(dst_path.stat().st_size)
                self._log(f'Concluído → {dst_path.name}  ({size})', 'ok')
            except Exception as exc:
                self._log(f'Erro: {exc}', 'err')
            finally:
                self._set_busy(False)

        threading.Thread(target=task, daemon=True).start()

    # ────────────────────────────────────────────────────────────────
    #   ABA: CHAVES RSA
    # ────────────────────────────────────────────────────────────────

    def _build_keys_tab(self):
        self.nb.add('  Chaves RSA  ')
        frame = self.nb.tab('  Chaves RSA  ')
        self._add_scroll_frame(frame, self._fill_keys_tab)

    def _fill_keys_tab(self, parent):
        gen_card = Card(parent, 'Gerar Novo Par de Chaves RSA-2048')
        gen_card.pack(fill='x', padx=4, pady=(0, 10))

        self._key_name = ctk.StringVar(value='minhas_chaves')
        self._key_priv = ctk.StringVar()
        self._key_pub  = ctk.StringVar()
        self._key_pp   = ctk.StringVar()

        def _update_paths(*_):
            name = self._key_name.get().strip() or 'minhas_chaves'
            self._key_priv.set(str(KEYS_DIR / f'{name}_private.pem'))
            self._key_pub.set(str(KEYS_DIR / f'{name}_public.pem'))

        self._key_name.trace_add('write', _update_paths)
        _update_paths()

        fields = [
            ('Nome do perfil:',            self._key_name, None),
            ('Chave privada (.pem):',      self._key_priv, None),
            ('Chave pública (.pem):',      self._key_pub,  None),
            ('Senha da chave (opcional):', self._key_pp,   '•'),
        ]
        for label, var, show in fields:
            row = ctk.CTkFrame(gen_card.inner, fg_color='transparent')
            row.pack(fill='x', pady=3)
            ctk.CTkLabel(row, text=label, text_color=DIM,
                         font=ctk.CTkFont(*FONT_LABEL), anchor='w', width=200).pack(side='left')
            kw = {'show': show} if show else {}
            _make_entry(row, var=var, **kw).pack(side='left', fill='x', expand=True)

        # Botões
        btn_row = ctk.CTkFrame(parent, fg_color='transparent')
        btn_row.pack(fill='x', padx=4, pady=(0, 10))
        _make_btn(btn_row, '⚙   Gerar Par de Chaves', self._run_gen_keys,
                  primary=True, height=40).pack(side='left')
        _make_btn(btn_row, '↻   Atualizar lista', self._refresh_keys_list,
                  height=40).pack(side='left', padx=(10, 0))

        # Lista de chaves
        list_card = Card(parent, 'Chaves Disponíveis')
        list_card.pack(fill='both', expand=True, padx=4)

        self._keys_text = tk.Text(
            list_card.inner, height=7,
            bg=SURF3, fg=TEXT,
            font=FONT_MONO, relief='flat', bd=8,
            state='disabled',
            selectbackground=ACCENT, selectforeground=BG,
        )
        sb = tk.Scrollbar(list_card.inner, command=self._keys_text.yview,
                          bg=SURF3, troughcolor=SURF3,
                          activebackground=DIM, relief='flat', bd=0)
        self._keys_text.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self._keys_text.pack(side='left', fill='both', expand=True)
        self._refresh_keys_list()

    def _run_gen_keys(self):
        priv = Path(self._key_priv.get().strip())
        pub  = Path(self._key_pub.get().strip())
        pp   = self._key_pp.get()

        if not self._key_priv.get().strip() or not self._key_pub.get().strip():
            self._log('Informe os caminhos para as chaves.', 'warn'); return

        self._log('Gerando par de chaves RSA-2048…', 'info')
        self._set_busy(True)

        def task():
            try:
                RSAHandler.generate_keypair(priv, pub, pp)
                self._log(f'Chaves geradas!  {priv.name}  /  {pub.name}', 'ok')
                self.root.after(0, self._refresh_keys_list)
            except Exception as exc:
                self._log(f'Erro ao gerar chaves: {exc}', 'err')
            finally:
                self._set_busy(False)

        threading.Thread(target=task, daemon=True).start()

    def _refresh_keys_list(self):
        pems = sorted(KEYS_DIR.glob('*.pem')) if KEYS_DIR.exists() else []
        self._keys_text.configure(state='normal')
        self._keys_text.delete('1.0', 'end')
        if pems:
            for p in pems:
                size = _human_size(p.stat().st_size)
                self._keys_text.insert('end', f'  {p.name}  ({size})\n')
        else:
            self._keys_text.insert('end',
                f'  Nenhuma chave encontrada em:\n  {KEYS_DIR}\n')
        self._keys_text.configure(state='disabled')

    # ────────────────────────────────────────────────────────────────
    #   ABA: SOBRE
    # ────────────────────────────────────────────────────────────────

    def _build_about_tab(self):
        self.nb.add('  Sobre  ')
        frame = self.nb.tab('  Sobre  ')
        self._add_scroll_frame(frame, self._fill_about_tab)

    def _fill_about_tab(self, parent):
        alg_card = Card(parent, 'Algoritmos Suportados')
        alg_card.pack(fill='x', padx=4, pady=(0, 10))

        for h in REGISTRY.values():
            kind_color = GREEN if h.kind == 'simétrico' else PURPLE
            chip_fg    = '#0d2a1a' if h.kind == 'simétrico' else '#1e1033'

            row = ctk.CTkFrame(alg_card.inner, fg_color=SURF3, corner_radius=10)
            row.pack(fill='x', pady=4, ipady=4)

            # Badge do nome
            name_badge = ctk.CTkFrame(row, fg_color=ACCENT_DIM, corner_radius=8)
            name_badge.pack(side='left', padx=(12, 14), pady=8)
            ctk.CTkLabel(name_badge, text=h.name,
                         font=ctk.CTkFont('Consolas', 12, 'bold'),
                         text_color=ACCENT).pack(padx=12, pady=6)

            info_col = ctk.CTkFrame(row, fg_color='transparent')
            info_col.pack(side='left', fill='x', expand=True, pady=4)

            type_row = ctk.CTkFrame(info_col, fg_color='transparent')
            type_row.pack(anchor='w')

            # Chip de tipo
            chip = ctk.CTkFrame(type_row, fg_color=chip_fg, corner_radius=5)
            chip.pack(side='left', padx=(0, 8))
            ctk.CTkLabel(chip,
                         text=f'  {h.kind.capitalize()}  ',
                         font=ctk.CTkFont('Segoe UI', 10, 'bold'),
                         text_color=kind_color).pack(pady=2)

            ctk.CTkLabel(type_row, text=h.key_info,
                         font=ctk.CTkFont('Segoe UI', 10),
                         text_color=kind_color).pack(side='left')

            ctk.CTkLabel(info_col, text=h.description,
                         font=ctk.CTkFont('Segoe UI', 11),
                         text_color=DIM).pack(anchor='w', pady=(3, 0))

        notes_card = Card(parent, 'Recomendações')
        notes_card.pack(fill='x', padx=4)

        notes = [
            ('AES-256-GCM', GREEN,  'Padrão recomendado. Rápido, seguro e autenticado.'),
            ('3DES-CBC',    YELLOW, 'Legado. Use apenas por compatibilidade com sistemas antigos.'),
            ('RSA-2048',    PURPLE, 'Ideal para troca de chaves cifradas entre partes diferentes.'),
        ]
        for algo, color, desc in notes:
            row = ctk.CTkFrame(notes_card.inner, fg_color=SURF3, corner_radius=8)
            row.pack(fill='x', pady=3, ipady=4)

            ctk.CTkLabel(row, text=algo, width=100,
                         font=ctk.CTkFont('Consolas', 11, 'bold'),
                         text_color=color, anchor='w').pack(
                             side='left', padx=(12, 0))
            ctk.CTkLabel(row, text='→',
                         font=ctk.CTkFont('Segoe UI', 11),
                         text_color=DIM).pack(side='left', padx=(8, 8))
            ctk.CTkLabel(row, text=desc,
                         font=ctk.CTkFont('Segoe UI', 11),
                         text_color=DIM, anchor='w').pack(side='left')

    # ────────────────────────────────────────────────────────────────
    #   HELPERS
    # ────────────────────────────────────────────────────────────────

    def _add_scroll_frame(self, parent, fill_fn):
        """Cria um scroll container dentro de uma aba e chama fill_fn(inner)."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color='transparent',
                                        scrollbar_button_color=SURF3,
                                        scrollbar_button_hover_color=BORDER)
        scroll.pack(fill='both', expand=True, padx=4, pady=8)
        fill_fn(scroll)

    def _log(self, msg: str, level: str = 'info'):
        prefix = {'ok': '✔', 'err': '✘', 'warn': '⚠', 'info': '●'}.get(level, '●')

        def _write():
            self._log_text.configure(state='normal')
            self._log_text.insert('end', f'  {prefix}  {msg}\n', level)
            self._log_text.see('end')
            self._log_text.configure(state='disabled')

        self.root.after(0, _write)

    def _set_busy(self, busy: bool):
        def _update():
            self._busy = busy
            if busy:
                self.root.configure(cursor='wait')
                self._anim_val = 0.0
                self._animate()
            else:
                self.root.configure(cursor='')
                if self._anim_id:
                    self.root.after_cancel(self._anim_id)
                    self._anim_id = None
                self._progress.set(0)

        self.root.after(0, _update)

    def _animate(self):
        if not self._busy:
            return
        self._anim_val = (self._anim_val + 0.018) % 1.0
        self._progress.set(self._anim_val)
        self._anim_id = self.root.after(30, self._animate)


# ════════════════════════════════════════════════════════════════════
#   PONTO DE ENTRADA
# ════════════════════════════════════════════════════════════════════

def _human_size(n: float) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{n:.1f} {unit}' if unit != 'B' else f'{int(n)} B'
        n /= 1024
    return f'{n:.1f} PB'


def _suggest_enc_path(src: Path) -> Path:
    return src.parent / (src.name + '.enc')


def _suggest_dec_path(src: Path) -> Path:
    name = src.name
    return src.parent / (name[:-4] if name.endswith('.enc') else name + '.dec')


def _detect_handler(src: Path):
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


def run():
    root = ctk.CTk()
    CryptoFileGUI(root)
    root.mainloop()


if __name__ == '__main__':
    run()