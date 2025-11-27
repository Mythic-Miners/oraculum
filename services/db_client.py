from pymongo import MongoClient
import config # type: ignore

class DBClient(object):
    def __init__(self):
        self.client = MongoClient(config.MONGODB_URI)
        self.db = self.client.get_default_database()

    def insert(self, collection_name, document):
        collection = self.db[collection_name]
        result = collection.insert_one(document)
        return result.inserted_id

    def find(self, collection_name, query):
        collection = self.db[collection_name]
        return collection.find(query)

    def close(self):
        self.client.close()


mongo_client = DBClient()