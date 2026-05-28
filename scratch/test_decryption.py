import base64
import os
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def decrypt_whatsapp_media(encrypted_file_path: str, media_key_b64: str, media_type: str = "image") -> bytes:
    # 1. Base64 decode media key
    media_key = base64.b64decode(media_key_b64)
    
    # 2. Get info string based on media type
    info_map = {
        "image": b"WhatsApp Image Keys",
        "audio": b"WhatsApp Audio Keys",
        "video": b"WhatsApp Video Keys",
        "document": b"WhatsApp Document Keys"
    }
    info = info_map.get(media_type, b"WhatsApp Image Keys")
    
    # 3. Derive key stream using HKDF-SHA256
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=112,
        salt=b"\x00" * 32,
        info=info
    )
    key_stream = hkdf.derive(media_key)
    
    iv = key_stream[:16]
    aes_key = key_stream[16:48]
    
    # 4. Read encrypted file content
    with open(encrypted_file_path, "rb") as f:
        file_content = f.read()
        
    # Strip last 10 bytes (MAC)
    ciphertext = file_content[:-10]
    
    # 5. Decrypt using AES-CBC
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    # 6. Remove PKCS7 padding
    padding_len = plaintext[-1]
    if 0 < padding_len <= 16:
        # Check if padding is valid
        if all(x == padding_len for x in plaintext[-padding_len:]):
            plaintext = plaintext[:-padding_len]
            
    return plaintext

# Test the decryption
encrypted_path = "tmp/product_image_2a96900f7b75c74a3cd04b62dd91d97e.jpg"
media_key = "4PGeZ3nRqsef1RIJbYl+bietncxdUC7C3JF8jVWtA7M="
decrypted_path = "tmp/test_decrypted.jpg"

try:
    decrypted_bytes = decrypt_whatsapp_media(encrypted_path, media_key, "image")
    with open(decrypted_path, "wb") as f:
        f.write(decrypted_bytes)
    print("SUCCESS: Decrypted successfully!")
    print("Decrypted size:", os.path.getsize(decrypted_path))
    print("Decrypted magic bytes:", decrypted_bytes[:4])
except Exception as e:
    import traceback
    traceback.print_exc()
