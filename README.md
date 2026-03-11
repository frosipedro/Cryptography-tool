# 🔐 CryptoFile v1.0

**CryptoFile** is a file encryption and decryption tool developed in Python. The project supports three widely recognized algorithms — AES-256-GCM, 3DES-CBC, and RSA-2048 — and is accessible through both a modern graphical interface (GUI) and a terminal interface (CLI). The goal is to provide a simple, secure, and flexible solution for protecting local files, suitable for personal use as well as educational and technical purposes.

---

## 📋 Table of Contents

- [Features](#-features)
- [Supported Algorithms](#-supported-algorithms)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [How to Use](#-how-to-use)
  - [Graphical Interface (GUI)](#graphical-interface-gui)
  - [Terminal Interface (CLI)](#terminal-interface-cli)
- [Project Structure](#-project-structure)
- [Technical Details](#-technical-details)
  - [AES-256-GCM](#aes-256-gcm)
  - [3DES-CBC](#3des-cbc)
  - [RSA-2048](#rsa-2048)
- [RSA Key Management](#-rsa-key-management)
- [Security](#-security)
- [License](#-license)

---

## ✨ Features

- **Encryption and decryption** of any file type
- **3 available algorithms:** AES-256-GCM, 3DES-CBC, and RSA-2048 (hybrid)
- **Automatic detection** of the algorithm used during decryption
- **Modern graphical interface** with dark theme (Material Design 3) via `customtkinter`
- **Fully functional terminal interface** with an interactive file browser
- **Secure key derivation** via PBKDF2-HMAC-SHA256
- **Generation and management** of RSA-2048 key pairs (.pem)
- **Integrity authentication** on encrypted files (GCM tag / HMAC-SHA256)

---

## 🔑 Supported Algorithms

| Algorithm   | Type         | Key                            | Recommended for                              |
| ----------- | ------------ | ------------------------------ | -------------------------------------------- |
| AES-256-GCM | Symmetric    | Password (PBKDF2, 600k iters.) | General use — fast, secure, and authenticated |
| 3DES-CBC    | Symmetric    | Password (PBKDF2, 300k iters.) | Compatibility with legacy systems            |
| RSA-2048    | Asymmetric   | Public/private key pair        | Secure file exchange between parties         |

---

## 🖥️ Prerequisites

- Python **3.10** or higher
- pip

---

## 📦 Installation

**1. Clone the repository:**

```bash
git clone https://github.com/your-username/cryptography-tool.git
cd cryptography-tool
```

**2. Create and activate a virtual environment (recommended):**

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

**3. Install dependencies:**

```bash
pip install cryptography
pip install customtkinter   # optional — only required for the GUI
```

---

## 🚀 How to Use

### Graphical Interface (GUI)

Run without arguments to open the graphical interface:

```bash
python main.py
```

> **Requirement:** `customtkinter` must be installed. If it is not, the program will display a message guiding you to install it or use CLI mode.

The GUI is organized into four tabs:

| Tab          | Description                                                   |
| ------------ | ------------------------------------------------------------- |
| Encrypt      | Select a file, algorithm, and password/key to encrypt         |
| Decrypt      | Select an encrypted file and provide credentials              |
| RSA Keys     | Generate and list RSA-2048 key pairs (.pem)                   |
| About        | Information about the algorithms and recommendations          |

---

### Terminal Interface (CLI)

To use terminal mode:

```bash
python main.py --cli
```

You will navigate through interactive menus:

```
[1]  Encrypt file
[2]  Decrypt file
[3]  Manage RSA keys
[4]  About the algorithms
[0]  Exit
```

**Interrupting execution:** press `Ctrl+C` at any time to exit safely.

---

## 📁 Project Structure

```
cryptography-tool/
│
├── main.py                  # Entry point — GUI or CLI
│
├── crypto/
│   ├── __init__.py          # Central handler registry
│   ├── base.py              # Abstract CryptoHandler class
│   ├── aes_handler.py       # AES-256-GCM implementation
│   ├── des_handler.py       # 3DES-CBC implementation
│   └── rsa_handler.py       # RSA-2048 (hybrid) implementation
│
├── ui/
│   ├── gui.py               # Graphical interface (customtkinter)
│   └── terminal.py          # Terminal interface (ANSI/CLI)
│
├── utils/
│   └── file_utils.py        # File utilities and CLI file browser
│
├── requirements.txt         # (recommended to create — see below)
├── LICENSE
└── README.md
```

---

## 🔬 Technical Details

### AES-256-GCM

Authenticated symmetric algorithm. The key is derived from the password using PBKDF2-HMAC-SHA256 with 600,000 iterations. GCM mode simultaneously ensures **confidentiality** and **authenticity**, eliminating the need for an external HMAC.

**Encrypted file format:**

```
[MAGIC 9b] [SALT 16b] [NONCE 12b] [TAG 16b] [CIPHERTEXT]
```

---

### 3DES-CBC

Legacy symmetric algorithm (TripleDES). The 24-byte key is derived using PBKDF2-HMAC-SHA256 (300,000 iterations). Integrity is verified via **HMAC-SHA256** over the ciphertext.

**Encrypted file format:**

```
[MAGIC 9b] [SALT 16b] [IV 8b] [HMAC 32b] [CIPHERTEXT (PKCS7)]
```

> ⚠️ Use 3DES only when compatibility with legacy systems is required. For new projects, prefer AES-256-GCM.

---

### RSA-2048

Since RSA is not suitable for directly encrypting large data, a **hybrid** scheme is used:

1. A random AES-256 session key is generated
2. The file is encrypted with AES-256-GCM using that key
3. The session key is encrypted with the **RSA public key** (OAEP + SHA-256)

**Encrypted file format:**

```
[MAGIC 9b] [ENC_KEY_LEN 4b] [ENC_SESSION_KEY] [NONCE 12b] [TAG 16b] [CIPHERTEXT]
```

---

## 🗝️ RSA Key Management

RSA keys are stored in PEM format and saved by default at:

```
~/.cryptofile/keys/
```

**To generate a new key pair:**

- **GUI:** go to the _RSA Keys_ tab and fill in the form
- **CLI:** select option `[3] Manage RSA keys` → `[1] Generate new pair`

Two files will be created:

```
<name>_private.pem   ← private key (optionally password-protected)
<name>_public.pem    ← public key (can be shared freely)
```

> ⚠️ **Keep your private key in a safe place.** Without it, it is not possible to decrypt files encrypted with the corresponding public key.

---

## 🛡️ Security

- All key derivation uses **PBKDF2-HMAC-SHA256** with a high iteration count to resist brute-force attacks
- **AES-256-GCM** mode authenticates the ciphertext — any tampering is detected during decryption
- **3DES-CBC** uses a separate HMAC-SHA256 for integrity verification
- The RSA scheme uses **OAEP with SHA-256**, which is resistant to chosen-ciphertext attacks
- Passwords are never stored — only the derived salt is saved in the encrypted file

---

## 📄 License

Distributed under the **MIT** license. See the [LICENSE](LICENSE) file for more details.

---

## Credits

- Cristian dos Santos Siquiera — https://github.com/CristianSSiqueira
- Pedro Rockenbach Frosi — https://github.com/frosipedro
