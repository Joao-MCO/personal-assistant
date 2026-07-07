"""
Ingestão de arquivos de texto/markdown (READMEs, ADRs, docs de onboarding)
no Chroma -- irmã de app/utils/embedding.py, que só lida com PDF. Chunking
mais simples aqui: por número de caracteres, já que não há conceito de
"página" em markdown puro.

Usado para popular as coleções consultadas por RAGDaBaseDeCodigo
(tools/knowledge_rag.py) e OnboardingGuiado.
"""

import hashlib
import logging
import os
import uuid
from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from services.chroma import get_collection
from services.knowledge_tracking import registrar_documento_indexado
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

CHUNK_SIZE_CHARS = 3000
CHUNK_OVERLAP_CHARS = 300


def _split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if c.strip()]


def create_text_embedding(collection: str, directory: str) -> int:
    """
    Indexa todos os arquivos .md/.txt de `directory` na coleção `collection`
    do Chroma. Retorna quantos arquivos foram processados.

    Reindexação: se o arquivo já foi indexado antes com o mesmo conteúdo
    (mesmo content_hash em knowledge_documents), pula -- evita reprocessar
    (e pagar por embeddings de novo) sem necessidade a cada execução.
    """
    if not os.path.isdir(directory):
        logger.warning(f"Diretório '{directory}' não existe -- nada para indexar.")
        return 0

    collection_obj = get_collection(collection)
    embedding_func = GoogleGenerativeAIEmbeddings(model=Settings.gemini["embedding"])

    from db.base import SessionLocal
    from db.models import KnowledgeDocument

    processados = 0
    for filename in os.listdir(directory):
        if not filename.lower().endswith((".md", ".txt")):
            continue

        full_path = os.path.join(directory, filename)
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        db = SessionLocal()
        try:
            existing = (
                db.query(KnowledgeDocument)
                .filter(KnowledgeDocument.collection == collection, KnowledgeDocument.filename == filename)
                .first()
            )
            if existing is not None and existing.content_hash == content_hash:
                logger.info(f"'{filename}' sem mudanças desde a última indexação — pulando.")
                continue
        finally:
            db.close()

        chunks = _split_into_chunks(content)
        if not chunks:
            continue

        ids, embeddings, metadatas, docs = [], [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(str(uuid.uuid4()))
            embeddings.append(embedding_func.embed_query(chunk))
            metadatas.append({"doc": filename, "chunk": i})
            docs.append(chunk)

        collection_obj.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=docs)
        registrar_documento_indexado(collection, filename, len(chunks), content_hash)
        processados += 1
        logger.info(f"Indexado: {filename} ({len(chunks)} chunk(s)) em '{collection}'.")

    return processados