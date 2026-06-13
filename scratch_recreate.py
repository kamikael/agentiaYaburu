import asyncio
from sqlalchemy import text
from app.db import AsyncSessionLocal

async def recreate():
    commands = [
        "CREATE EXTENSION IF NOT EXISTS vector;",
        '''
        CREATE TABLE IF NOT EXISTS documents (
          id bigserial PRIMARY KEY,
          content text NOT NULL,
          metadata jsonb DEFAULT '{}',
          embedding vector(768)
        );
        ''',
        '''
        CREATE OR REPLACE FUNCTION match_documents (
          query_embedding vector(768),
          match_count int DEFAULT 5,
          filter jsonb DEFAULT '{}'
        )
        RETURNS TABLE (
          id bigint,
          content text,
          metadata jsonb,
          similarity float
        )
        LANGUAGE plpgsql
        AS $$
        #variable_conflict use_column
        BEGIN
          RETURN QUERY
          SELECT
            id,
            content,
            metadata,
            1 - (documents.embedding <=> query_embedding) AS similarity
          FROM documents
          WHERE metadata @> filter
          ORDER BY documents.embedding <=> query_embedding
          LIMIT match_count;
        END;
        $$;
        ''',
        '''
        CREATE INDEX IF NOT EXISTS documents_embedding_idx
        ON documents USING hnsw (embedding vector_cosine_ops);
        '''
    ]
    
    async with AsyncSessionLocal() as db:
        for cmd in commands:
            await db.execute(text(cmd))
        await db.commit()
    print("Documents table and match_documents function recreated successfully.")

if __name__ == "__main__":
    asyncio.run(recreate())
