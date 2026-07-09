"""
Helper compartilhado entre app/utils/embedding.py (ingestão de PDFs) e
services/text_ingestion.py (ingestão de texto/markdown): registra em
`knowledge_documents` que um arquivo foi indexado no Chroma. Extraído pra cá
pra não duplicar a mesma lógica nos dois lugares.
"""

import logging

logger = logging.getLogger(__name__)


def registrar_documento_indexado(collection: str, filename: str, num_pages: int, content_hash: str) -> None:
    """
    Registra (ou atualiza) que um arquivo foi indexado no Chroma -- os
    vetores continuam só no Chroma, isso é apenas o controle/auditoria de
    cima: o que já foi indexado, quando, e se o conteúdo mudou desde a
    última vez (via content_hash).

    Uma falha aqui não deve impedir a indexação em si (que já aconteceu no
    Chroma antes desta chamada) -- por isso o try/except só loga o erro.
    """
    try:
        from db.base import SessionLocal
        from db.models import KnowledgeDocument

        db = SessionLocal()
        try:
            row = (
                db.query(KnowledgeDocument)
                .filter(KnowledgeDocument.collection == collection, KnowledgeDocument.filename == filename)
                .first()
            )
            if row is None:
                row = KnowledgeDocument(collection=collection, filename=filename)
                db.add(row)
            row.num_pages = num_pages
            row.content_hash = content_hash
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception(f"Falha ao registrar '{filename}' em knowledge_documents (indexação no Chroma não é afetada)")