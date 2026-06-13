-- Migration 003: user-generated problems support
-- owner_user_id NULL = curated/global problem; non-null = visible only to that user
ALTER TABLE problems
    ADD COLUMN IF NOT EXISTS owner_user_id UUID NULL
        REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_problems_owner_user_id
    ON problems(owner_user_id)
    WHERE owner_user_id IS NOT NULL;
