"""Secret partage F4 (serveur-compromis) <-> F5 (memoire-vive).

L'archive /var/tmp/.cache/x.enc plantee dans l'image disque F4 est chiffree
avec CETTE cle AES-256-CTR. En F5, la cle est detenue par le binaire fileless
(ELF lance via memfd_create), stockee XORee avec un masque derive du PID. Le
joueur extrait l'ELF du dump memoire, le reverse, demasque la cle, et dechiffre
x.enc -> flag F5.

Ces constantes sont la reference unique : gen.py de F4 et le kit de build F5
les importent tous les deux.
"""

# Flag revele par le dechiffrement de x.enc (etape finale de F5).
F5_FLAG = "FPS{memfd_elf_fileless_cle_aes_masquee_par_le_pid}"

# AES-256-CTR. 'KEY' est la cle reelle ; en memoire elle est stockee
# KEY XOR mask(PID), ou mask = sha256(str(pid)) tronque a 32 octets.
KEY = bytes.fromhex(
    "a3f1c09b7d42e85610fe23ab9c7d04e5"
    "11b8aa72c6390f5d84e7021bcd9a6f38")
NONCE = bytes.fromhex("0011223344556677")  # 8 octets (prefix CTR)


def encrypt(plaintext: bytes) -> bytes:
    from Crypto.Cipher import AES
    c = AES.new(KEY, AES.MODE_CTR, nonce=NONCE)
    return c.encrypt(plaintext)


def decrypt(ciphertext: bytes) -> bytes:
    from Crypto.Cipher import AES
    c = AES.new(KEY, AES.MODE_CTR, nonce=NONCE)
    return c.decrypt(ciphertext)


def mask_key_for_pid(pid: int) -> bytes:
    """Representation 'en memoire' de la cle : KEY XOR sha256(pid)[:32]."""
    import hashlib
    mask = hashlib.sha256(str(pid).encode()).digest()
    return bytes(a ^ b for a, b in zip(KEY, mask))
