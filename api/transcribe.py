import json
import os
import re
import io
from http.server import BaseHTTPRequestHandler

from youtube_transcript_api import YouTubeTranscriptApi
import requests


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


def buscar_transcricao(url: str) -> str:
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
    return "\n".join(linhas)


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = self.rfile.read(tamanho)

        try:
            dados = json.loads(corpo)
            url = dados.get("url", "").strip()
            if not url:
                raise ValueError("URL não informada.")

            transcricao = buscar_transcricao(url)
            video_id = extrair_video_id(url)
            resposta = {"transcript": transcricao, "video_id": video_id}
            status = 200
        except ValueError as e:
            resposta = {"error": str(e)}
            status = 400
        except Exception as e:
            resposta = {"error": f"Erro ao buscar transcrição: {str(e)}"}
            status = 500

        corpo_resposta = json.dumps(resposta, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo_resposta)))
        self.end_headers()
        self.wfile.write(corpo_resposta)

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        pass
