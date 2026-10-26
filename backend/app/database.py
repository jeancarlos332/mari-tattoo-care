
import psycopg

from app.config import settings


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS artists (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(150) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash TEXT,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS clients (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(150) NOT NULL,
        phone VARCHAR(30),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tattoo_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        artist_id UUID NOT NULL REFERENCES artists(id),
        client_id UUID NOT NULL REFERENCES clients(id),
        tattoo_description TEXT,
        tattooed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        follow_up_days INTEGER NOT NULL DEFAULT 30
            CHECK (follow_up_days BETWEEN 1 AND 365),
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID NOT NULL
            REFERENCES tattoo_sessions(id) ON DELETE CASCADE,
        day_number INTEGER NOT NULL CHECK (day_number BETWEEN 1 AND 365),
        observation VARCHAR(1000),
        recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (session_id, day_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS photos (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        daily_log_id UUID NOT NULL
            REFERENCES daily_logs(id) ON DELETE CASCADE,
        storage_key TEXT NOT NULL UNIQUE,
        content_type VARCHAR(100) NOT NULL,
        size_bytes BIGINT NOT NULL CHECK (size_bytes > 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS access_tokens (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID NOT NULL
            REFERENCES tattoo_sessions(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL UNIQUE,
        token_encrypted TEXT,
        expires_at TIMESTAMPTZ NOT NULL,
        revoked_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
]


def check_database_connection() -> bool:
    with psycopg.connect(
        settings.database_url,
        connect_timeout=10,
        port=5432,
        sslmode="require",
        channel_binding="disable",
    ) as connection:
        result = connection.execute("SELECT 1").fetchone()

    return result == (1,)


def initialize_database() -> None:
    with psycopg.connect(
        settings.database_url,
        connect_timeout=10,
        port=5432,
        sslmode="require",
        channel_binding="disable",
    ) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)

        connection.execute(
            """
            ALTER TABLE access_tokens
            ADD COLUMN IF NOT EXISTS token_encrypted TEXT
            """
        )
