import os
import uuid
from functools import wraps
from hmac import compare_digest
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from assistente import extrair_texto_pdf, responder
from config import (
    EXTENSOES_PERMITIDAS,
    FLASK_SECRET_KEY,
    LOGIN_EMAIL,
    LOGIN_PASSWORD,
    MAX_MENSAGENS_HISTORICO,
    PASTA_UPLOADS,
    TAMANHO_MAXIMO_ARQUIVO_MB,
)
from database import (
    excluir_documento,
    inserir_documento,
    listar_pacientes,
    obter_dados_paciente,
)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = TAMANHO_MAXIMO_ARQUIVO_MB * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Histórico curto por paciente. Os dados clínicos não ficam aqui: são relidos do
# PostgreSQL a cada mensagem para que a LLM receba sempre o estado atualizado.
historicos: dict[int, list[dict]] = {}


def login_obrigatorio(funcao):
    @wraps(funcao)
    def rota_protegida(*args, **kwargs):
        if session.get("autenticado"):
            return funcao(*args, **kwargs)

        if request.path.startswith("/api/"):
            return jsonify({"erro": "Sua sessão expirou. Entre novamente."}), 401

        return redirect(url_for("login"))

    return rota_protegida


def extensao_permitida(nome_arquivo: str) -> bool:
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS
    )


def _id_paciente(valor) -> int:
    try:
        paciente_id = int(valor)
    except (TypeError, ValueError):
        raise ValueError("Paciente inválido.")
    if paciente_id <= 0:
        raise ValueError("Paciente inválido.")
    return paciente_id


@app.errorhandler(413)
def arquivo_grande(_erro):
    return jsonify({"erro": f"O arquivo excede {TAMANHO_MAXIMO_ARQUIVO_MB} MB."}), 413


@app.route("/")
@login_obrigatorio
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("autenticado"):
        return redirect(url_for("index"))

    erro = None
    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        email_valido = compare_digest(email, LOGIN_EMAIL.lower())
        senha_valida = compare_digest(senha, LOGIN_PASSWORD)

        if email_valido and senha_valida:
            session.clear()
            session["autenticado"] = True
            session["email"] = LOGIN_EMAIL
            return redirect(url_for("index"))

        erro = "E-mail ou senha incorretos. Tente novamente."

    return render_template("login.html", erro=erro, email=email)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/pacientes", methods=["GET"])
@login_obrigatorio
def api_pacientes():
    try:
        return jsonify({"pacientes": listar_pacientes()})
    except Exception as exc:
        return jsonify({"erro": f"Não foi possível acessar o PostgreSQL: {exc}"}), 500


@app.route("/api/pacientes/<int:paciente_id>", methods=["GET"])
@login_obrigatorio
def api_paciente(paciente_id: int):
    try:
        dados = obter_dados_paciente(paciente_id)
    except Exception as exc:
        return jsonify({"erro": f"Erro ao consultar o banco: {exc}"}), 500

    if not dados:
        return jsonify({"erro": "Paciente não encontrado."}), 404

    # Não enviamos o texto completo dos PDFs para o navegador; ele é usado pela LLM no servidor.
    documentos_publicos = [
        {
            "id": doc["id"],
            "nome_arquivo": doc["nome_arquivo"],
            "tipo_arquivo": doc["tipo_arquivo"],
            "data_upload": doc["data_upload"],
        }
        for doc in dados["documentos"]
    ]

    return jsonify(
        {
            "paciente": dados["paciente"],
            "medicoes": dados["medicoes"],
            "medicamentos": dados["medicamentos"],
            "documentos": documentos_publicos,
        }
    )


@app.route("/api/mensagem", methods=["POST"])
@login_obrigatorio
def api_mensagem():
    corpo = request.get_json(silent=True) or {}
    mensagem = str(corpo.get("mensagem", "")).strip()

    if not mensagem:
        return jsonify({"erro": "Mensagem vazia."}), 400

    try:
        paciente_id = _id_paciente(corpo.get("paciente_id"))
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400

    try:
        dados = obter_dados_paciente(paciente_id)
        if not dados:
            return jsonify({"erro": "Paciente não encontrado."}), 404

        historico = historicos.setdefault(paciente_id, [])
        resposta = responder(mensagem, dados, historico)

        historico.append({"role": "user", "content": mensagem})
        historico.append({"role": "assistant", "content": resposta})
        if len(historico) > MAX_MENSAGENS_HISTORICO:
            del historico[:-MAX_MENSAGENS_HISTORICO]

        return jsonify({"resposta": resposta})
    except Exception as exc:
        return jsonify({"erro": f"Não foi possível gerar a resposta: {exc}"}), 500


@app.route("/api/upload", methods=["POST"])
@login_obrigatorio
def api_upload():
    arquivo = request.files.get("arquivo")

    try:
        paciente_id = _id_paciente(request.form.get("paciente_id"))
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400

    if arquivo is None or not arquivo.filename:
        return jsonify({"erro": "Nenhum arquivo enviado."}), 400

    if not extensao_permitida(arquivo.filename):
        return jsonify({"erro": "Por enquanto, somente arquivos PDF são aceitos."}), 400

    nome_original = secure_filename(arquivo.filename)
    if not nome_original:
        return jsonify({"erro": "Nome de arquivo inválido."}), 400

    try:
        dados = obter_dados_paciente(paciente_id)
        if not dados:
            return jsonify({"erro": "Paciente não encontrado."}), 404
    except Exception as exc:
        return jsonify({"erro": f"Erro ao consultar o paciente: {exc}"}), 500

    pasta_paciente = PASTA_UPLOADS / str(paciente_id)
    pasta_paciente.mkdir(parents=True, exist_ok=True)
    nome_salvo = f"{uuid.uuid4().hex}_{nome_original}"
    caminho = pasta_paciente / nome_salvo
    arquivo.save(caminho)

    try:
        texto = extrair_texto_pdf(str(caminho))
        if not texto:
            caminho.unlink(missing_ok=True)
            return jsonify(
                {
                    "erro": (
                        "O PDF não possui texto extraível. PDFs escaneados como imagem "
                        "precisam de OCR antes do envio."
                    )
                }
            ), 400

        caminho_relativo = os.path.relpath(caminho, start=os.path.dirname(__file__))
        documento = inserir_documento(
            paciente_id=paciente_id,
            nome_arquivo=nome_original,
            tipo_arquivo=arquivo.mimetype or "application/pdf",
            caminho_arquivo=caminho_relativo,
            texto_extraido=texto,
        )
    except Exception as exc:
        caminho.unlink(missing_ok=True)
        return jsonify({"erro": f"Não foi possível registrar o documento: {exc}"}), 500

    return jsonify({"documento": documento}), 201


@app.route(
    "/api/pacientes/<int:paciente_id>/documentos/<int:documento_id>",
    methods=["DELETE"],
)
@login_obrigatorio
def api_excluir_documento(paciente_id: int, documento_id: int):
    try:
        documento = excluir_documento(documento_id, paciente_id)
    except Exception as exc:
        return jsonify({"erro": f"Não foi possível remover o documento: {exc}"}), 500

    if not documento:
        return jsonify({"erro": "Documento não encontrado para este paciente."}), 404

    # O caminho vem do banco, por isso só apagamos arquivos que estejam dentro
    # da pasta de uploads da aplicação.
    caminho_salvo = Path(documento["caminho_arquivo"])
    caminho = caminho_salvo if caminho_salvo.is_absolute() else Path(__file__).parent / caminho_salvo
    caminho = caminho.resolve()
    pasta_uploads = PASTA_UPLOADS.resolve()

    aviso = None
    if caminho.is_relative_to(pasta_uploads):
        try:
            caminho.unlink(missing_ok=True)
        except OSError:
            aviso = "O registro foi removido, mas não foi possível apagar o arquivo do disco."
    else:
        aviso = "O registro foi removido; o caminho do arquivo não era um upload válido."

    # Evita que respostas baseadas no documento excluído permaneçam no contexto
    # enviado à LLM em perguntas posteriores.
    historicos.pop(paciente_id, None)

    resposta = {"ok": True, "nome_arquivo": documento["nome_arquivo"]}
    if aviso:
        resposta["aviso"] = aviso
    return jsonify(resposta)


@app.route("/api/chat/limpar", methods=["POST"])
@login_obrigatorio
def api_limpar_chat():
    corpo = request.get_json(silent=True) or {}
    try:
        paciente_id = _id_paciente(corpo.get("paciente_id"))
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400

    historicos.pop(paciente_id, None)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
