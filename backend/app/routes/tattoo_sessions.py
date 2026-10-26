
import hashlib
import secrets
from datetime import datetime
from uuid import UUID

import psycopg
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.config import settings
from app.schemas import (
    TattooSessionCreate,
    TattooSessionCreated,
    TattooFollowUpAccess,
)


router = APIRouter(
    prefix="/api/tattoo-sessions",
    tags=["Tattoo sessions"],
)


def get_token_cipher() -> Fernet:
    try:
        return Fernet(settings.token_encryption_key.encode("utf-8"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La clave de cifrado de tokens no está configurada correctamente.",
        ) from None


def create_access_token() -> tuple[str, str, str]:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    token_encrypted = get_token_cipher().encrypt(
        raw_token.encode("utf-8")
    ).decode("utf-8")

    return raw_token, token_hash, token_encrypted


def build_access_url(raw_token: str) -> str:
    base_url = settings.frontend_base_url.rstrip("/")
    return f"{base_url}/seguimiento?token={raw_token}"


def database_connection():
    return psycopg.connect(
        settings.database_url,
        connect_timeout=10,
        port=5432,
        sslmode="require",
        channel_binding="disable",
    )


@router.post(
    "",
    response_model=TattooSessionCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_tattoo_session(payload: TattooSessionCreate):
    raw_token, token_hash, token_encrypted = create_access_token()

    try:
        with database_connection() as connection:
            artist = connection.execute(
                """
                SELECT id
                FROM artists
                WHERE id = %s AND active = TRUE
                """,
                (payload.artist_id,),
            ).fetchone()

            if artist is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No se encontró un tatuador activo con ese ID.",
                )

            client = connection.execute(
                """
                INSERT INTO clients (name, phone)
                VALUES (%s, %s)
                RETURNING id
                """,
                (payload.client_name, payload.client_phone),
            ).fetchone()

            client_id = client[0]

            session = connection.execute(
                """
                INSERT INTO tattoo_sessions (
                    artist_id,
                    client_id,
                    tattoo_description,
                    tattooed_at,
                    follow_up_days
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, artist_id, tattooed_at, follow_up_days
                """,
                (
                    payload.artist_id,
                    client_id,
                    payload.tattoo_description,
                    payload.tattooed_at,
                    payload.follow_up_days,
                ),
            ).fetchone()

            token_row = connection.execute(
                """
                INSERT INTO access_tokens (
                    session_id,
                    token_hash,
                    token_encrypted,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    NOW() + (%s * INTERVAL '1 day')
                )
                RETURNING expires_at
                """,
                (
                    session[0],
                    token_hash,
                    token_encrypted,
                    session[3],
                ),
            ).fetchone()

            return TattooSessionCreated(
                session_id=session[0],
                client_id=client_id,
                artist_id=session[1],
                client_name=payload.client_name,
                tattooed_at=session[2],
                follow_up_days=session[3],
                access_url=build_access_url(raw_token),
                access_expires_at=token_row[0],
            )

    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible guardar el tatuaje. Inténtalo nuevamente.",
        ) from None


@router.get("")
def list_tattoo_sessions(
    artist_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        with database_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    ts.id AS session_id,
                    c.id AS client_id,
                    c.name AS client_name,
                    c.phone AS client_phone,
                    a.id AS artist_id,
                    a.name AS artist_name,
                    ts.tattoo_description,
                    ts.tattooed_at,
                    ts.follow_up_days,
                    ts.active,
                    ts.created_at
                FROM tattoo_sessions ts
                JOIN clients c ON c.id = ts.client_id
                JOIN artists a ON a.id = ts.artist_id
                WHERE ts.artist_id = %s
                ORDER BY ts.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (artist_id, limit, offset),
            ).fetchall()

            columns = [
                "session_id",
                "client_id",
                "client_name",
                "client_phone",
                "artist_id",
                "artist_name",
                "tattoo_description",
                "tattooed_at",
                "follow_up_days",
                "active",
                "created_at",
            ]

            return [
                {
                    column: (
                        value.isoformat()
                        if isinstance(value, datetime)
                        else str(value)
                        if isinstance(value, UUID)
                        else value
                    )
                    for column, value in zip(columns, row)
                }
                for row in rows
            ]

    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar los seguimientos.",
        ) from None



@router.get("/{session_id}/access-link")
def get_session_access_link(
    session_id: UUID,
    artist_id: UUID = Query(...),
):
    """
    Devuelve el QR vigente o genera automáticamente un nuevo acceso
    para la misma sesión cuando no existe un enlace recuperable.
    """
    try:
        with database_connection() as connection:
            # Bloqueamos la sesión para evitar regeneraciones simultáneas.
            session = connection.execute(
                """
                SELECT ts.follow_up_days
                FROM tattoo_sessions ts
                JOIN artists a ON a.id = ts.artist_id
                WHERE ts.id = %s
                  AND ts.artist_id = %s
                  AND ts.active = TRUE
                  AND a.active = TRUE
                FOR UPDATE OF ts
                """,
                (session_id, artist_id),
            ).fetchone()

            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No se encontró una sesión activa para ese tatuador.",
                )

            # Buscar el último enlace que todavía sea válido.
            row = connection.execute(
                """
                SELECT token_encrypted, expires_at
                FROM access_tokens
                WHERE session_id = %s
                  AND revoked_at IS NULL
                  AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()

            # Si el enlace puede recuperarse, reutilizarlo.
            if row is not None and row[0]:
                try:
                    raw_token = get_token_cipher().decrypt(
                        row[0].encode("utf-8")
                    ).decode("utf-8")

                    return {
                        "session_id": str(session_id),
                        "access_url": build_access_url(raw_token),
                        "access_expires_at": row[1].isoformat(),
                    }

                except (InvalidToken, ValueError):
                    # La clave cambió o el token no se puede descifrar.
                    # Se creará uno nuevo para esta misma sesión.
                    pass

            # No existe un enlace recuperable: revocar los anteriores
            # que sigan activos y crear uno nuevo.
            connection.execute(
                """
                UPDATE access_tokens
                SET revoked_at = NOW()
                WHERE session_id = %s
                  AND revoked_at IS NULL
                """,
                (session_id,),
            )

            raw_token, token_hash, token_encrypted = create_access_token()

            token_row = connection.execute(
                """
                INSERT INTO access_tokens (
                    session_id,
                    token_hash,
                    token_encrypted,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    NOW() + (%s * INTERVAL '1 day')
                )
                RETURNING expires_at
                """,
                (
                    session_id,
                    token_hash,
                    token_encrypted,
                    session[0],
                ),
            ).fetchone()

            return {
                "session_id": str(session_id),
                "access_url": build_access_url(raw_token),
                "access_expires_at": token_row[0].isoformat(),
            }

    except HTTPException:
        raise
    except psycopg.Error:
        import logging
        logging.getLogger(__name__).exception(
            "Error de base de datos al recuperar o crear el acceso QR."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible recuperar el acceso QR. Revisa los logs del backend.",
        ) from None


@router.post("/{session_id}/access-link/regenerate")
def regenerate_session_access_link(
    session_id: UUID,
    artist_id: UUID = Query(...),
):
    """Revoca los enlaces anteriores y crea uno nuevo para la misma sesión."""
    raw_token, token_hash, token_encrypted = create_access_token()

    try:
        with database_connection() as connection:
            session = connection.execute(
                """
                SELECT ts.follow_up_days
                FROM tattoo_sessions ts
                JOIN artists a ON a.id = ts.artist_id
                WHERE ts.id = %s
                  AND ts.artist_id = %s
                  AND ts.active = TRUE
                  AND a.active = TRUE
                FOR UPDATE OF ts
                """,
                (session_id, artist_id),
            ).fetchone()

            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No se encontró una sesión activa para ese tatuador.",
                )

            connection.execute(
                """
                UPDATE access_tokens
                SET revoked_at = NOW()
                WHERE session_id = %s
                  AND revoked_at IS NULL
                """,
                (session_id,),
            )

            token_row = connection.execute(
                """
                INSERT INTO access_tokens (
                    session_id,
                    token_hash,
                    token_encrypted,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    NOW() + (%s * INTERVAL '1 day')
                )
                RETURNING expires_at
                """,
                (
                    session_id,
                    token_hash,
                    token_encrypted,
                    session[0],
                ),
            ).fetchone()

            return {
                "session_id": str(session_id),
                "access_url": build_access_url(raw_token),
                "access_expires_at": token_row[0].isoformat(),
            }

    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible regenerar el acceso. Inténtalo nuevamente.",
        ) from None


@router.get(
    "/access/{token}",
    response_model=TattooFollowUpAccess,
)
def get_tattoo_follow_up(token: str):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    try:
        with database_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    ts.id,
                    c.name,
                    a.name,
                    ts.tattoo_description,
                    ts.tattooed_at,
                    ts.follow_up_days,
                    at.expires_at
                FROM access_tokens at
                JOIN tattoo_sessions ts ON ts.id = at.session_id
                JOIN clients c ON c.id = ts.client_id
                JOIN artists a ON a.id = ts.artist_id
                WHERE at.token_hash = %s
                  AND at.expires_at > NOW()
                  AND at.revoked_at IS NULL
                  AND ts.active = TRUE
                  AND a.active = TRUE
                LIMIT 1
                """,
                (token_hash,),
            ).fetchone()

            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        "El enlace no es válido, ha vencido "
                        "o ya no está disponible."
                    ),
                )

            return TattooFollowUpAccess(
                session_id=row[0],
                client_name=row[1],
                artist_name=row[2],
                tattoo_description=row[3],
                tattooed_at=row[4],
                follow_up_days=row[5],
                access_expires_at=row[6],
            )

    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar el seguimiento.",
        ) from None


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_tattoo_session(
    session_id: UUID,
    artist_id: UUID = Query(...),
):
    try:
        with database_connection() as connection:
            session = connection.execute(
                """
                SELECT client_id
                FROM tattoo_sessions
                WHERE id = %s AND artist_id = %s
                """,
                (session_id, artist_id),
            ).fetchone()

            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No se encontró el seguimiento solicitado.",
                )

            client_id = session[0]

            connection.execute(
                """
                DELETE FROM tattoo_sessions
                WHERE id = %s AND artist_id = %s
                """,
                (session_id, artist_id),
            )

            connection.execute(
                """
                DELETE FROM clients
                WHERE id = %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM tattoo_sessions
                      WHERE client_id = %s
                  )
                """,
                (client_id, client_id),
            )

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible eliminar el seguimiento.",
        ) from None
