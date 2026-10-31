"""Acesso ao PostgreSQL.

O projeto espera as tabelas:
- paciente(id, nome, idade)
- medicoes(id, paciente_id, data, glicemia, hba1c, peso)
- medicamentos(id, paciente_id, nome, dose, data_inicio, data_fim)
- documentos(id, paciente_id, nome_arquivo, tipo_arquivo, caminho_arquivo,
             texto_extraido, data_upload)
"""

import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from config import (
    MAX_DOCUMENTOS_NO_CONTEXTO,
    MAX_MEDICAMENTOS_NO_CONTEXTO,
    MAX_MEDICOES_NO_CONTEXTO,
)


def _parametros_conexao():
    url = os.getenv("DATABASE_URL")
    if url:
        return {"conninfo": url}

    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "postgres"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


@contextmanager
def conexao():
    params = _parametros_conexao()
    if "conninfo" in params:
        conn = psycopg.connect(params["conninfo"], row_factory=dict_row)
    else:
        conn = psycopg.connect(**params, row_factory=dict_row)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_pacientes() -> list[dict]:
    with conexao() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, nome, idade FROM paciente ORDER BY nome")
        return list(cur.fetchall())


def obter_paciente(paciente_id: int) -> dict | None:
    with conexao() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, nome, idade FROM paciente WHERE id = %s",
            (paciente_id,),
        )
        return cur.fetchone()


def listar_medicoes(paciente_id: int, limite: int = MAX_MEDICOES_NO_CONTEXTO) -> list[dict]:
    with conexao() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, paciente_id, data, glicemia, hba1c, peso
            FROM medicoes
            WHERE paciente_id = %s
            ORDER BY data DESC, id DESC
            LIMIT %s
            """,
            (paciente_id, limite),
        )
        return list(cur.fetchall())


def listar_medicamentos(
    paciente_id: int, limite: int = MAX_MEDICAMENTOS_NO_CONTEXTO
) -> list[dict]:
    with conexao() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, paciente_id, nome, dose, data_inicio, data_fim
            FROM medicamentos
            WHERE paciente_id = %s
            ORDER BY data_inicio DESC NULLS LAST, id DESC
            LIMIT %s
            """,
            (paciente_id, limite),
        )
        return list(cur.fetchall())


def listar_documentos(
    paciente_id: int, limite: int = MAX_DOCUMENTOS_NO_CONTEXTO
) -> list[dict]:
    with conexao() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, paciente_id, nome_arquivo, tipo_arquivo, caminho_arquivo,
                   texto_extraido, data_upload
            FROM documentos
            WHERE paciente_id = %s
            ORDER BY data_upload DESC, id DESC
            LIMIT %s
            """,
            (paciente_id, limite),
        )
        return list(cur.fetchall())


def inserir_documento(
    paciente_id: int,
    nome_arquivo: str,
    tipo_arquivo: str,
    caminho_arquivo: str,
    texto_extraido: str,
) -> dict:
    with conexao() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documentos (
                paciente_id,
                nome_arquivo,
                tipo_arquivo,
                caminho_arquivo,
                texto_extraido
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, paciente_id, nome_arquivo, tipo_arquivo,
                      caminho_arquivo, data_upload
            """,
            (
                paciente_id,
                nome_arquivo,
                tipo_arquivo,
                caminho_arquivo,
                texto_extraido,
            ),
        )
        return cur.fetchone()


def excluir_documento(documento_id: int, paciente_id: int) -> dict | None:
    """Remove um documento pertencente ao paciente e retorna seus metadados."""
    with conexao() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM documentos
            WHERE id = %s AND paciente_id = %s
            RETURNING id, paciente_id, nome_arquivo, caminho_arquivo
            """,
            (documento_id, paciente_id),
        )
        return cur.fetchone()


def obter_dados_paciente(paciente_id: int) -> dict | None:
    paciente = obter_paciente(paciente_id)
    if not paciente:
        return None

    return {
        "paciente": paciente,
        "medicoes": listar_medicoes(paciente_id),
        "medicamentos": listar_medicamentos(paciente_id),
        "documentos": listar_documentos(paciente_id),
    }
