import pymongo

db_url = "mongodb+srv://vitvalef_db_user:yftZ097dE2hrlAbY@cluster0.c6x0pdu.mongodb.net/?appName=Cluster0"
client = pymongo.MongoClient(db_url)
db = client.get_database("antigravity")

count = db.market_overviews.count_documents({})
print(f"market_overviews count: {count}")

count_summaries = db.market_summaries.count_documents({})
print(f"market_summaries count: {count_summaries}")
