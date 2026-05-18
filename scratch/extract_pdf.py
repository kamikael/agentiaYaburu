import pypdf
import os

pdf_path = "Chatbot-Intelligent-Yaburu (4).pdf"
output_path = "pdf_analysis.txt"

if os.path.exists(pdf_path):
    with open(pdf_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Text extracted to {output_path}")
else:
    print(f"File {pdf_path} not found")
