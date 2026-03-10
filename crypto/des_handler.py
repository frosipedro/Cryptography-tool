"""
3DES-CBC (TripleDES) — criptografia simétrica legada.

Formato do arquivo cifrado:
  [MAGIC 9b] [SALT 16b] [IV 8b] [HMAC 32b] [CIPHERTEXT (PKCS7)]

A chave (24 bytes) é derivada com PBKDF2-HMAC-SHA256.
A integridade é garantida por HMAC-SHA256 sobre o ciphertext.
"""

import os
import hmac
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, modes
try:
    # cryptography >= 43: TripleDES movido para o módulo 'decrepit'
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
except ImportError:
    from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from .base import CryptoHandler

MAGIC      = b'CF3DESCBC'   # 9 bytes
SALT_LEN   = 16
IV_LEN     = 8
HMAC_LEN   = 32
KEY_LEN    = 24             # 3DES requer 24 bytes (192 bits)
ITERATIONS = 300_000
BLOCK_SIZE = 64             # bits (8 bytes) para DES/3DES


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))


def _hmac_sha256(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


class DESHandler(CryptoHandler):

    MAGIC = MAGIC

    @property
    def name(self) -> str:
        return '3DES-CBC'

    @property
    def kind(self) -> str:
        return 'simétrico'

    @property
    def description(self) -> str:
        return 'TripleDES com HMAC-SHA256. Compatibilidade com sistemas legados.'

    @property
    def key_info(self) -> str:
        return 'Senha (derivada via PBKDF2-HMAC-SHA256, 300k iter.)'

    # ── Encrypt ────────────────────────────────────────────────────

    def encrypt_file(self, src: Path, dst: Path, **_) -> dict:
        password: str = _['password']
        plaintext = self._read(src)

        salt = os.urandom(SALT_LEN)
        iv   = os.urandom(IV_LEN)
        key  = _derive_key(password, salt)

        # PKCS7 padding
        padder  = PKCS7(BLOCK_SIZE).padder()
        padded  = padder.update(plaintext) + padder.finalize()

        cipher     = Cipher(TripleDES(key), modes.CBC(iv))
        encryptor  = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        mac  = _hmac_sha256(key, ciphertext)
        blob = MAGIC + salt + iv + mac + ciphertext
        self._write(dst, blob)

        return {
            'algorithm' : self.name,
            'salt_hex'  : salt.hex(),
            'iv_hex'    : iv.hex(),
            'key_source': 'senha fornecida pelo usuário',
        }

    # ── Decrypt ────────────────────────────────────────────────────

    def decrypt_file(self, src: Path, dst: Path, **_) -> None:
        password: str = _['password']
        blob = self._read(src)

        magic_len = len(MAGIC)
        if blob[:magic_len] != MAGIC:
            raise ValueError('Arquivo não é um arquivo 3DES-CBC válido.')

        offset     = magic_len
        salt       = blob[offset: offset + SALT_LEN];  offset += SALT_LEN
        iv         = blob[offset: offset + IV_LEN];    offset += IV_LEN
        stored_mac = blob[offset: offset + HMAC_LEN];  offset += HMAC_LEN
        ciphertext = blob[offset:]

        key = _derive_key(password, salt)

        # Verifica integridade
        expected_mac = _hmac_sha256(key, ciphertext)
        if not hmac.compare_digest(stored_mac, expected_mac):
            raise ValueError('Falha na verificação de integridade (HMAC inválido). '
                             'Senha incorreta ou arquivo corrompido.')

        cipher    = Cipher(TripleDES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded    = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove padding
        unpadder  = PKCS7(BLOCK_SIZE).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()

        self._write(dst, plaintext)