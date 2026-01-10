import chromadb
from chromadb.utils.embedding_functions.google_embedding_function import GoogleGenerativeAiEmbeddingFunction
from utils.settings import Settings

def get_client():
    client = chromadb.CloudClient(
            api_key=Settings.chroma['api_key'],
            tenant=Settings.chroma['tenant'],
            database=Settings.chroma['database']
        )
    
    return client

def get_collection(name):
    client = get_client()
    collection = client.get_or_create_collection(
        name=name,
        embedding_function=GoogleGenerativeAiEmbeddingFunction(
            api_key=Settings.gemini['api_key'],
            model_name=Settings.gemini['embedding']
        )
    )
    return collection