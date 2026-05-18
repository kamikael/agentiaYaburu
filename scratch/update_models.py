import os

models_dir = r"c:\Users\kamikael\Desktop\tout\agentiaYaburu\app\models"

for filename in os.listdir(models_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        filepath = os.path.join(models_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        content = content.replace("from sqlalchemy.orm import declarative_base", "")
        content = content.replace("Base = declarative_base()", "from app.db import Base")
        
        # Clean up double newlines that might result
        content = content.replace("\n\n\n", "\n\n")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

print("Updated all models to use app.db.Base")
