import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env", override=True)

MODEL_ASSISTENTE = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

# Autenticação simples para o protótipo. Em produção, defina estes valores no .env.
LOGIN_EMAIL = os.getenv("LOGIN_EMAIL", "admin@glycoassist.local")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "admin")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

PASTA_UPLOADS = BASE_DIR / "uploads"
EXTENSOES_PERMITIDAS = {"pdf"}
TAMANHO_MAXIMO_ARQUIVO_MB = 15
MAX_CARACTERES_POR_DOCUMENTO = 5000
MAX_DOCUMENTOS_NO_CONTEXTO = 5
MAX_MEDICOES_NO_CONTEXTO = 20
MAX_MEDICAMENTOS_NO_CONTEXTO = 20
MAX_MENSAGENS_HISTORICO = 12

PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)
