import pymongo

db_url = "mongodb+srv://vitvalef_db_user:yftZ097dE2hrlAbY@cluster0.c6x0pdu.mongodb.net/?appName=Cluster0"
client = pymongo.MongoClient(db_url)
db = client.get_database("antigravity")

cols = db.list_collection_names()
print(f"Collections: {cols}")

for col in cols:
    count = db[col].count_documents({})
    print(f"Collection: {col}, Count: {count}")
    
