-- Add GitHub OAuth token storage for terminal git auth
ALTER TABLE users ADD COLUMN IF NOT EXISTS github_access_token TEXT;
