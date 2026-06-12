-- ProofForge initial schema
-- All tables use gen_random_uuid() which is built-in to PostgreSQL 13+

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id           VARCHAR(50)  UNIQUE NOT NULL,
    github_login        VARCHAR(100) NOT NULL,
    name                VARCHAR(200),
    email               VARCHAR(200),
    avatar_url          TEXT,
    career_track        VARCHAR(50),
    current_difficulty  VARCHAR(20)  NOT NULL DEFAULT 'junior',
    total_score         INTEGER      NOT NULL DEFAULT 0,
    issues_resolved     INTEGER      NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_active_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS problems (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(100) UNIQUE NOT NULL,
    title           VARCHAR(300) NOT NULL,
    description     TEXT         NOT NULL,
    difficulty      VARCHAR(20)  NOT NULL,
    category        VARCHAR(50)  NOT NULL,
    track           VARCHAR(50)  NOT NULL,
    language        VARCHAR(30)  NOT NULL,
    docker_image    VARCHAR(200) NOT NULL,
    codebase_key    VARCHAR(300) NOT NULL,
    test_suite_key  VARCHAR(300) NOT NULL,
    time_limit_mins INTEGER      NOT NULL DEFAULT 120,
    points          INTEGER      NOT NULL DEFAULT 100,
    display_order   INTEGER      NOT NULL DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    optimal_hint    TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS active_sessions (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id    UUID        NOT NULL REFERENCES problems(id),
    status        VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, problem_id)
);

CREATE TABLE IF NOT EXISTS submissions (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID        NOT NULL REFERENCES users(id),
    problem_id     UUID        NOT NULL REFERENCES problems(id),
    session_id     UUID        REFERENCES active_sessions(id),
    status         VARCHAR(30) NOT NULL DEFAULT 'queued',
    code_snapshot  JSONB       NOT NULL,
    storage_key    VARCHAR(300),
    score          INTEGER,
    review_id      UUID,
    attempt_number INTEGER     NOT NULL DEFAULT 1,
    time_taken_mins INTEGER,
    submitted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS reviews (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id        UUID        UNIQUE NOT NULL REFERENCES submissions(id),
    verdict              VARCHAR(30) NOT NULL,
    overall_score        INTEGER     NOT NULL,
    score_breakdown      JSONB       NOT NULL,
    summary              TEXT        NOT NULL,
    inline_comments      JSONB       NOT NULL,
    learning_resources   JSONB,
    architectural_note   TEXT,
    ast_score            INTEGER,
    security_score       INTEGER,
    test_score           INTEGER,
    perf_score           INTEGER,
    ast_output           JSONB,
    security_output      JSONB,
    test_output          JSONB,
    llm_raw              TEXT,
    pipeline_duration_ms INTEGER,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolio_cards (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID         UNIQUE NOT NULL REFERENCES users(id),
    issues_resolved  INTEGER      NOT NULL DEFAULT 0,
    avg_score        NUMERIC(5,2) NOT NULL DEFAULT 0,
    skill_percentile INTEGER      NOT NULL DEFAULT 0,
    skill_radar      JSONB        NOT NULL DEFAULT '{}',
    highlights       JSONB        NOT NULL DEFAULT '[]',
    resolution_log   JSONB        NOT NULL DEFAULT '[]',
    card_hash        VARCHAR(200),
    signature        VARCHAR(500),
    signed_at        TIMESTAMPTZ,
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_cases (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id  UUID         NOT NULL REFERENCES problems(id),
    name        VARCHAR(200) NOT NULL,
    is_visible  BOOLEAN      NOT NULL DEFAULT TRUE,
    test_code   TEXT,
    weight      NUMERIC(3,2) NOT NULL DEFAULT 1.0,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for hot query paths
CREATE INDEX IF NOT EXISTS idx_submissions_user_id
    ON submissions(user_id);

CREATE INDEX IF NOT EXISTS idx_submissions_status
    ON submissions(status)
    WHERE status != 'completed';

CREATE INDEX IF NOT EXISTS idx_problems_track_difficulty
    ON problems(track, difficulty)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_reviews_submission_id
    ON reviews(submission_id);

CREATE INDEX IF NOT EXISTS idx_portfolio_user_id
    ON portfolio_cards(user_id);
