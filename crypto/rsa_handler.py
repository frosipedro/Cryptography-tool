"""
RSA-2048 — criptografia assimétrica (híbrida RSA + AES-256-GCM).

Como RSA sozinho não cifra arquivos grandes, usamos criptografia híbrida:
  1. Gerar uma chave de sessão AES-256 aleatória
  2. Cifrar o arquivo com AES-256-GCM usando essa chave
  3. Cifrar a chave de sessão com a chave pública RSA (OAEP + SHA-256)

Formato do arquivo cifrado:
  [MAGIC 9b] [ENC_KEY_LEN 4b] [ENC_SESSION_KEY] [NONCE 12b] [TAG 16b] [CIPHERTEXT]

Chaves RSA são salvas em PEM:
  private_key.pem  — chave privada (protegida por senha opcional)
  public_key.pem   — chave pública
"""

import os
import struct
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .base import CryptoHandler

MAGIC          = b'CFRSA2048'   # 9 bytes
NONCE_LEN      = 12
TAG_LEN        = 16
SESSION_KEY_LEN = 32            # AES-256
RSA_KEY_BITS   = 2048
PUBLIC_EXP     = 65537


class RSAHandler(CryptoHandler):

    MAGIC = MAGIC

    @property
    def name(self) -> str:
        return 'RSA-2048'

    @property
    def kind(self) -> str:
        return 'assimétrico'

    @property
    def description(self) -> str:
        return 'Par de chaves pública/privada. Híbrido RSA + AES-256-GCM.'

    @property
    def key_info(self) -> str:
        return 'Par de chaves RSA-2048 (arquivos .pem)'

    # ── Geração de par de chaves ────────────────────────────────────

    @staticmethod
    def generate_keypair(private_path: Path, public_path: Path,
                         passphrase: str = '') -> None:
        """Gera e salva par de chaves RSA-2048 em formato PEM."""
        private_key = rsa.generate_private_key(
            public_exponent=PUBLIC_EXP,
            key_size=RSA_KEY_BITS,
        )

        enc_alg = (
            serialization.BestAvailableEncryption(passphrase.encode())
            if passphrase
            else serialization.NoEncryption()
        )

        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=enc_alg,
        )

        pem_public = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        private_path.parent.mkdir(parents=True, exist_ok=True)
        private_path.write_bytes(pem_private)
        public_path.write_bytes(pem_public)

    # ── Loaders ────────────────────────────────────────────────────

    @staticmethod
    def load_private_key(path: Path, passphrase: str = '') -> RSAPrivateKey:
        pwd = passphrase.encode() if passphrase else None
        key = serialization.load_pem_private_key(path.read_bytes(), password=pwd)
        if not isinstance(key, RSAPrivateKey):
            raise TypeError('A chave privada fornecida não é uma chave RSA.')
        return key

    @staticmethod
    def load_public_key(path: Path) -> RSAPublicKey:
        key = serialization.load_pem_public_key(path.read_bytes())
        if not isinstance(key, RSAPublicKey):
            raise TypeError('A chave pública fornecida não é uma chave RSA.')
        return key

    # ── Encrypt ────────────────────────────────────────────────────

    def encrypt_file(self, src: Path, dst: Path, **kwargs) -> dict:
        public_key_path: Path = kwargs['public_key_path']
        plaintext   = self._read(src)
        public_key  = self.load_public_key(public_key_path)

        # Chave de sessão AES-256 aleatória
        session_key = os.urandom(SESSION_KEY_LEN)
        nonce       = os.urandom(NONCE_LEN)

        # Cifra o arquivo com AES-GCM
        aesgcm     = AESGCM(session_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)   # inclui tag
        tag        = ciphertext[-TAG_LEN:]
        cipher_body = ciphertext[:-TAG_LEN]

        # Cifra a chave de sessão com RSA-OAEP
        enc_session_key = public_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        enc_key_len = struct.pack('>I', len(enc_session_key))
        blob = MAGIC + enc_key_len + enc_session_key + nonce + tag + cipher_body
        self._write(dst, blob)

        return {
            'algorithm'      : self.name,
            'public_key_used': str(public_key_path),
            'key_source'     : 'chave pública RSA (arquivo .pem)',
        }

    # ── Decrypt ────────────────────────────────────────────────────

    def decrypt_file(self, src: Path, dst: Path, **kwargs) -> None:
        private_key_path: Path = kwargs['private_key_path']
        passphrase: str = kwargs.get('passphrase', '')
        blob = self._read(src)

        magic_len = len(MAGIC)
        if blob[:magic_len] != MAGIC:
            raise ValueError('Arquivo não é um arquivo RSA-2048 válido.')

        offset      = magic_len
        enc_key_len = struct.unpack('>I', blob[offset: offset + 4])[0]
        offset     += 4
        enc_sk      = blob[offset: offset + enc_key_len]; offset += enc_key_len
        nonce       = blob[offset: offset + NONCE_LEN];   offset += NONCE_LEN
        tag         = blob[offset: offset + TAG_LEN];     offset += TAG_LEN
        cipher_body = blob[offset:]

        private_key = self.load_private_key(private_key_path, passphrase)

        # Decifra a chave de sessão com RSA
        session_key = private_key.decrypt(
            enc_sk,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # Decifra o conteúdo com AES-GCM
        aesgcm    = AESGCM(session_key)
        plaintext = aesgcm.decrypt(nonce, cipher_body + tag, None)

        self._write(dst, plaintext)