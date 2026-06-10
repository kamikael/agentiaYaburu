import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from app.db import AsyncSessionLocal
from app.services.embedding_service import embedding_service
from app.services.chunking_service import chunking_service
from config import settings

logger = logging.getLogger(__name__)

class RagService:
    async def ingest_document(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Découpe le texte en chunks, génère les embeddings et les insère dans la base.
        """
        metadata = metadata or {}
        
        # 1. Chunking
        chunks = chunking_service.split_text(content)
        if not chunks:
            return {"status": "error", "message": "Aucun contenu à traiter."}

        # 2. Embedding
        # On peut embed en batch pour optimiser
        embeddings = await embedding_service.embed_texts(chunks)

        if len(chunks) != len(embeddings):
            return {"status": "error", "message": "Mismatch between chunks and embeddings"}

        # 3. Insertion en base
        async with AsyncSessionLocal() as db:
            insert_query = text("""
                INSERT INTO documents (content, metadata, embedding)
                VALUES (:content, :metadata, :embedding)
            """)
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = i
                
                await db.execute(insert_query, {
                    "content": chunk,
                    "metadata": json.dumps(chunk_metadata),
                    "embedding": f"[{','.join(map(str, embeddings[i]))}]"
                })
                
            await db.commit()
            
        return {
            "status": "success", 
            "chunks_processed": len(chunks),
            "metadata": metadata
        }

    async def search(self, query: str, top_k: int = None, similarity_threshold: float = None, metadata_filter: dict = None) -> List[Dict[str, Any]]:
        """
        Recherche vectorielle pour trouver les chunks les plus pertinents.
        """
        top_k = top_k or settings.RAG_TOP_K
        similarity_threshold = similarity_threshold or settings.RAG_SIMILARITY_THRESHOLD
        metadata_filter = metadata_filter or {}
        
        try:
            # 1. Embed query
            query_embedding = await embedding_service.embed_query(query)
            
            # 2. Search via Supabase RPC function (match_documents)
            async with AsyncSessionLocal() as db:
                # Appel de la fonction match_documents
                search_query = text("""
                    SELECT id, content, metadata, similarity
                    FROM match_documents(
                        CAST(:embedding_str AS vector),
                        :match_count,
                        CAST(:filter_json AS jsonb)
                    )
                    WHERE similarity >= :threshold
                """)
                
                result = await db.execute(search_query, {
                    "embedding_str": f"[{','.join(map(str, query_embedding))}]",
                    "match_count": top_k,
                    "filter_json": json.dumps(metadata_filter),
                    "threshold": similarity_threshold
                })
                
                rows = result.fetchall()
                
                documents = []
                for row in rows:
                    documents.append({
                        "id": row.id,
                        "content": row.content,
                        "metadata": row.metadata,
                        "similarity": row.similarity
                    })
                    
                return documents
                
        except Exception as e:
            logger.error(f"Erreur lors de la recherche vectorielle: {e}")
            return []

    async def list_documents_summary(self) -> List[Dict[str, Any]]:
        """
        Liste les sources uniques indexées.
        """
        async with AsyncSessionLocal() as db:
            query = text("""
                SELECT metadata->>'source' as source, metadata->>'title' as title, count(*) as chunk_count
                FROM documents
                WHERE metadata->>'source' IS NOT NULL
                GROUP BY metadata->>'source', metadata->>'title'
            """)
            result = await db.execute(query)
            rows = result.fetchall()
            return [{"source": r.source, "title": r.title, "chunk_count": r.chunk_count} for r in rows]

    async def delete_document_by_source(self, source: str) -> bool:
        """
        Supprime tous les chunks associés à une source.
        """
        async with AsyncSessionLocal() as db:
            query = text("""
                DELETE FROM documents
                WHERE metadata->>'source' = :source
            """)
            await db.execute(query, {"source": source})
            await db.commit()
            return True

    async def get_chunks_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les enregistrements (chunks) d'un document spécifique via sa source.
        """
        async with AsyncSessionLocal() as db:
            query = text("""
                SELECT id, content, metadata
                FROM documents
                WHERE metadata->>'source' = :source
                ORDER BY (metadata->>'chunk_index')::int ASC
            """)
            result = await db.execute(query, {"source": source})
            rows = result.fetchall()
            return [{"id": r.id, "content": r.content, "metadata": r.metadata} for r in rows]

    async def update_chunk(self, doc_id: str, new_content: str) -> bool:
        """
        Met à jour le contenu d'un enregistrement et régénère son embedding.
        """
        try:
            # 1. Générer le nouvel embedding pour le contenu
            new_embedding = await embedding_service.embed_query(new_content)
            
            # 2. Mettre à jour en base
            async with AsyncSessionLocal() as db:
                update_query = text("""
                    UPDATE documents
                    SET content = :content,
                        embedding = :embedding
                    WHERE id = :id
                """)
                await db.execute(update_query, {
                    "id": int(doc_id),
                    "content": new_content,
                    "embedding": f"[{','.join(map(str, new_embedding))}]"
                })
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du chunk {doc_id}: {e}")
            return False

rag_service = RagService()
