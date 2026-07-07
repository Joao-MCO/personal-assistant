import hashlib
import logging
import math
import os
import uuid

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pypdf import PdfReader

from services.chroma import get_collection
from services.knowledge_tracking import registrar_documento_indexado

logger = logging.getLogger(__name__)


def create_embedding(collection: str):
    collection_obj = get_collection(collection)
    embedding_func = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    dados_dir = "dados"
    files = os.listdir(dados_dir)
    for path in files:
        # os.path.join em vez do "dados\\{path}" hardcoded: o separador de
        # caminho do Windows quebrava a leitura em Linux/Mac.
        full_path = os.path.join(dados_dir, path)
        with open(full_path, "rb") as file:
            file_bytes = file.read()
            content_hash = hashlib.md5(file_bytes).hexdigest()

        with open(full_path, "rb") as file:
            reader = PdfReader(file)
            num_pages = reader.get_num_pages()
            for j in range(math.ceil(num_pages / 300)):
                start = j * 300
                end = (j + 1) * 300 if (j + 1) * 300 < num_pages else (num_pages - j * 300) + start
                ids = []
                embeddings = []
                metadatas = []
                docs = []
                for i in range(start, end):
                    text = reader.pages[i].extract_text()
                    metadata = {
                        "doc": path,
                        "page": i + 1
                    }
                    logger.info(f"Processando embedding: {metadata}")

                    page_id = f"{uuid.uuid4()}"
                    embed = embedding_func.embed_query(text)
                    ids.append(page_id)
                    embeddings.append(embed)
                    metadatas.append(metadata)
                    docs.append(text)
                collection_obj.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=docs
                )

        registrar_documento_indexado(collection, path, num_pages, content_hash)

    return True