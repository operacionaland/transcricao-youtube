import os
import re
import requests
from flask import Flask, request, jsonify, send_from_directory
from youtube_transcript_api import YouTubeTranscriptApi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)


def extrair_video_id(url: str) -> str:
    padrao = r"(?:v=|youtu\.be/|shorts/|live/)([a-zA-Z0-9_-]{11})"
    match = re.search(padrao, url)
    if not match:
        raise ValueError("URL do YouTube inválida ou não reconhecida.")
    return match.group(1)


def carregar_cookies_da_env() -> dict:
    conteudo = os.environ.get("YOUTUBE_COOKIES", "")
    cookies = {}
    for linha in conteudo.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = linha.split("\t")
        if len(partes) >= 7:
            cookies[partes[5]] = partes[6]
    return cookies


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "public"), "index.html")


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    dados = request.get_json(silent=True) or {}
    url = dados.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL não informada."}), 400

    try:
        video_id = extrair_video_id(url)

        session = requests.Session()
        cookies = carregar_cookies_da_env()
        if cookies:
            session.cookies.update(cookies)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        })

        ytt_api = YouTubeTranscriptApi(http_client=session)
        trechos = ytt_api.fetch(video_id, languages=["pt", "pt-BR", "en"])
        linhas = [t.text for t in trechos if t.text.strip()]

        return jsonify({"transcript": "\n".join(linhas), "video_id": video_id})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar transcrição: {str(e)}"}), 500
