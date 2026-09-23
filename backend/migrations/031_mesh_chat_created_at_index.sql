-- Ensure index on created_at exists for retention deletion queries (SEC-19).
CREATE INDEX IF NOT EXISTS idx_mesh_chat_created_at ON mesh_chat (created_at);
