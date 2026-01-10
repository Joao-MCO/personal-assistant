from pypdf import PdfReader
from chroma import get_collection
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
import uuid
import math

def create_embedding():
    collection = get_collection("rpg_collection")
    embedding_func = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    files = os.listdir("dados")
    for path in files:
        with open(f'dados\\{path}', 'rb') as file:
            reader = PdfReader(file)
            for j in range(math.ceil(reader.get_num_pages()/300)):
                start = j*300
                end = (j+1)*300 if (j+1)*300 < reader.get_num_pages() else (reader.get_num_pages() - j*300)+start
                ids = []
                embeddings = []
                metadatas = []
                docs = []
                for i in range(start, end):
                    text = reader.pages[i].extract_text()
                    metadata = {
                        "doc": path,
                        "page": i+1
                    }
                    print(metadata)
                    page_id = f"{uuid.uuid4()}"
                    embed = embedding_func.embed_query(text)
                    ids.append(page_id)
                    embeddings.append(embed)
                    metadatas.append(metadata)
                    docs.append(text)
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=docs
                )
                
        
    return True