"""
AES-256-GCM — criptografia simétrica autenticada.

Formato do arquivo cifrado:
  [MAGIC 12b] [SALT 16b] [NONCE 12b] [TAG 16b] [CIPHERTEXT]

A chave AES é derivada da senha com PBKDF2-HMAC-SHA256 (600 000 iterações).
O GCM fornece confidencialidade + autenticidade (não precisa de HMAC separado).
"""

import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from .base import CryptoHandler

MAGIC      = b'CFAES256G'   # 9 bytes
SALT_LEN   = 16
NONCE_LEN  = 12
TAG_LEN    = 16
KEY_LEN    = 32             # AES-256
ITERATIONS = 600_000


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))


class AESHandler(CryptoHandler):

    MAGIC = MAGIC

    @property
    def name(self) -> str:
        return 'AES-256-GCM'

    @property
    def kind(self) -> str:
        return 'simétrico'

    @property
    def description(self) -> str:
        return 'Rápido, seguro e autenticado. Padrão da indústria.'

    @property
    def key_info(self) -> str:
        return 'Senha (derivada via PBKDF2-HMAC-SHA256, 600k iter.)'

    # ── Encrypt ────────────────────────────────────────────────────

    def encrypt_file(self, src: Path, dst: Path, **kwargs) -> dict:
        plaintext = self._read(src)

        password = kwargs.get('password', '')
        salt  = os.urandom(SALT_LEN)
        nonce = os.urandom(NONCE_LEN)
        key   = _derive_key(password, salt)

        aesgcm     = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        # AESGCM.encrypt já adiciona o tag (16 bytes) no final do ciphertext

        # Separa ciphertext e tag para armazenar explicitamente
        tag        = ciphertext[-TAG_LEN:]
        cipher_body = ciphertext[:-TAG_LEN]

        blob = MAGIC + salt + nonce + tag + cipher_body
        self._write(dst, blob)

        return {
            'algorithm': self.name,
            'salt_hex' : salt.hex(),
            'nonce_hex': nonce.hex(),
            'key_source': 'senha fornecida pelo usuário',
        }

    # ── Decrypt ────────────────────────────────────────────────────

    def decrypt_file(self, src: Path, dst: Path, **kwargs) -> None:
        blob = self._read(src)

        password = kwargs.get('password', '')
        magic_len = len(MAGIC)
        if blob[:magic_len] != MAGIC:
            raise ValueError('Arquivo não é um arquivo AES-256-GCM válido.')

        offset     = magic_len
        salt       = blob[offset: offset + SALT_LEN];  offset += SALT_LEN
        nonce      = blob[offset: offset + NONCE_LEN]; offset += NONCE_LEN
        tag        = blob[offset: offset + TAG_LEN];   offset += TAG_LEN
        cipher_body = blob[offset:]

        key    = _derive_key(password, salt)
        aesgcm = AESGCM(key)

        # Re-concatena cipher_body + tag como o AESGCM espera
        plaintext = aesgcm.decrypt(nonce, cipher_body + tag, None)
        self._write(dst, plaintext)