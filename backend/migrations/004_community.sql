-- Community feature: posts (doubts), text answers, and up/down votes.
-- Usernames reuse users.github_login (no new identity).

CREATE TABLE IF NOT EXISTS community_posts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         VARCHAR(300) NOT NULL,
    body          TEXT NOT NULL DEFAULT '',
    image_key     TEXT,                         -- MinIO object key, null if no image
    image_type    VARCHAR(100),                 -- content-type, used when serving the image
    score         INTEGER NOT NULL DEFAULT 0,   -- denormalized sum of votes
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS community_answers (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id    UUID NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body       TEXT NOT NULL,
    score      INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One vote row per user per target. value is -1 or 1; removing a vote deletes the row.
-- Score counters on posts/answers are kept in sync from this table.
CREATE TABLE IF NOT EXISTS community_votes (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(10) NOT NULL CHECK (target_type IN ('post', 'answer')),
    target_id   UUID NOT NULL,
    value       SMALLINT NOT NULL CHECK (value IN (-1, 1)),
    PRIMARY KEY (user_id, target_type, target_id)
);

CREATE INDEX IF NOT EXISTS idx_community_posts_created ON community_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_posts_score   ON community_posts(score DESC);
CREATE INDEX IF NOT EXISTS idx_community_answers_post  ON community_answers(post_id, created_at);
CREATE INDEX IF NOT EXISTS idx_community_votes_target  ON community_votes(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_users_login_search      ON users(github_login);
