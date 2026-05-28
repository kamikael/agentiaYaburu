import os

file_path = "tmp/product_image_2a96900f7b75c74a3cd04b62dd91d97e.jpg"
if os.path.exists(file_path):
    with open(file_path, "rb") as f:
        content = f.read(100)
    print("File size:", os.path.getsize(file_path))
    print("First 100 bytes:", content)
    if b"<html" in content or b"<HTML" in content or b"{" in content:
        print("WARNING: This looks like HTML or JSON, not a binary image!")
else:
    print("File does not exist!")
