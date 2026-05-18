import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.bfgbhomlnlcebgfczwpu:Kamikael123%40@aws-1-eu-west-3.pooler.supabase.com:6543/postgres"

indexes = [
    "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
    "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_shops_user_id ON shops(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_shops_yaburu_id ON shops(yaburu_shop_id);",
    "CREATE INDEX IF NOT EXISTS idx_shops_is_primary ON shops(is_primary) WHERE is_primary = TRUE;",
    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_shop_id ON sessions(shop_id);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active) WHERE is_active = TRUE;",
    "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);",
    "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_conversations_shop_id ON conversations(shop_id);",
    "CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);",
    "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_conversations_last_message ON conversations(last_message_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);",
    "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);",
    "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_messages_whatsapp_id ON messages(whatsapp_message_id);",
    "CREATE INDEX IF NOT EXISTS idx_conv_history_conversation_id ON conversation_history(conversation_id);",
    "CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding ON rag_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
    "CREATE INDEX IF NOT EXISTS idx_rag_documents_type ON rag_documents(document_type);",
    "CREATE INDEX IF NOT EXISTS idx_rag_documents_category ON rag_documents(category);",
    "CREATE INDEX IF NOT EXISTS idx_rag_documents_active ON rag_documents(is_active) WHERE is_active = TRUE;",
    "CREATE INDEX IF NOT EXISTS idx_rag_documents_content_trgm ON rag_documents USING gin (content gin_trgm_ops);",
    "CREATE INDEX IF NOT EXISTS idx_rag_retrievals_user_id ON rag_retrievals(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_rag_retrievals_conversation_id ON rag_retrievals(conversation_id);",
    "CREATE INDEX IF NOT EXISTS idx_rag_retrievals_message_id ON rag_retrievals(message_id);",
    "CREATE INDEX IF NOT EXISTS idx_rag_retrievals_created_at ON rag_retrievals(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_user ON admin_logs(admin_user_id);",
    "CREATE INDEX IF NOT EXISTS idx_admin_logs_action_type ON admin_logs(action_type);",
    "CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_logs(created_at DESC);"
]

async def restore_indexes():
    engine = create_async_engine(DATABASE_URL, connect_args={"statement_cache_size": 0})
    async with engine.begin() as conn:
        for idx_sql in indexes:
            print(f"Executing: {idx_sql}")
            await conn.execute(text(idx_sql))
    await engine.dispose()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(restore_indexes())
