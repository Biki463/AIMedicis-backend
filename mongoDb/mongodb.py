# dbconnection/mongodb.py
from pymongo import MongoClient
import os

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "AIMedicis"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
