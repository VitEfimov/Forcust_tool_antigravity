import os

content = """DATABASE_URL=mongodb+srv://vitvalef_db_user:yftZ097dE2hrlAbY@cluster0.c6x0pdu.mongodb.net/antigravity?appName=Cluster0
STORAGE_TYPE=mongo
LOCAL_DATA_DIR=data/local
"""

with open(".env", "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully wrote .env")
