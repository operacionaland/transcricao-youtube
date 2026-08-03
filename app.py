import os
import re
import json
import html as html_module
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Transcrição YouTube</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f0f0f;
      color: #e8e8e8;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px 16px;
    }

    .container {
      width: 100%;
      max-width: 720px;
    }

    h1 {
      font-size: 1.6rem;
      font-weight: 600;
      margin-bottom: 8px;
      color: #fff;
    }

    .subtitle {
      font-size: 0.9rem;
      color: #888;
      margin-bottom: 32px;
    }

    .input-row {
      display: flex;
      gap: 10px;
    }

    input[type="text"] {
      flex: 1;
      padding: 12px 16px;
      border-radius: 8px;
      border: 1px solid #333;
      background: #1a1a1a;
      color: #e8e8e8;
      font-size: 0.95rem;
      outline: none;
      transition: border-color 0.2s;
    }

    input[type="text"]:focus {
      border-color: #ff4444;
    }

    input[type="text"]::placeholder {
      color: #555;
    }

    button {
      padding: 12px 22px;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      font-size: 0.95rem;
      font-weight: 500;
      transition: background 0.2s, opacity 0.2s;
    }

    .btn-primary {
      background: #ff4444;
      color: #fff;
    }

    .btn-primary:hover { background: #e03333; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      background: #2a2a2a;
      color: #ccc;
      border: 1px solid #333;
    }

    .btn-secondary:hover { background: #333; }

    .output-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 28px;
      margin-bottom: 10px;
    }

    .output-label {
      font-size: 0.85rem;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    textarea {
      width: 100%;
      height: 420px;
      padding: 16px;
      border-radius: 8px;
      border: 1px solid #333;
      background: #1a1a1a;
      color: #e8e8e8;
      font-size: 0.9rem;
      line-height: 1.6;
      resize: vertical;
      outline: none;
      font-family: inherit;
    }

    .status {
      margin-top: 12px;
      font-size: 0.85rem;
      min-height: 20px;
    }

    .status.erro { color: #ff6b6b; }
    .status.ok   { color: #6bffa5; }
    .status.info { color: #888; }

    .spinner {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid #555;
      border-top-color: #ff4444;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      vertical-align: middle;
      margin-right: 6px;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    .copied-badge {
      font-size: 0.78rem;
      color: #6bffa5;
      margin-left: 8px;
      opacity: 0;
      transition: opacity 0.3s;
    }

    .copied-badge.visible { opacity: 1; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Transcrição de Vídeo</h1>
    <p class="subtitle">Cole a URL de um vídeo ou live do YouTube abaixo</p>

    <div class="input-row">
      <input
        id="urlInput"
        type="text"
        placeholder="https://www.youtube.com/watch?v=... ou /live/..."
        autocomplete="off"
        spellcheck="false"
      />
      <button class="btn-primary" id="btnTranscrever" onclick="transcrever()">
        Transcrever
      </button>
    </div>

    <div class="output-header">
      <span class="output-label">Transcrição</span>
      <div>
        <button class="btn-secondary" onclick="copiar()">Copiar</button>
        <span class="copied-badge" id="copiedBadge">Copiado!</span>
      </div>
    </div>

    <textarea id="output" readonly placeholder="A transcrição aparecerá aqui..."></textarea>

    <div class="status info" id="status"></div>
  </div>

  <script>
    const urlInput    = document.getElementById("urlInput");
    const btnTrans    = document.getElementById("btnTranscrever");
    const output      = document.getElementById("output");
    const statusEl    = document.getElementById("status");
    const copiedBadge = document.getElementById("copiedBadge");

    urlInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") transcrever();
    });

    async function transcrever() {
      const url = urlInput.value.trim();
      if (!url) {
        setStatus("Cole uma URL antes de continuar.", "erro");
        return;
      }

      setStatus('<span class="spinner"></span>Buscando transcrição...', "info");
      output.value = "";
      btnTrans.disabled = true;

      try {
        const resp = await fetch("/api/transcribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });

        const dados = await resp.json();

        if (!resp.ok || dados.error) {
          setStatus(dados.error || "Erro desconhecido.", "erro");
        } else {
          output.value = dados.transcript;
          const linhas = dados.transcript.split("\n").filter(Boolean).length;
          setStatus(`Transcrição concluída — ${linhas} segmentos (vídeo: ${dados.video_id})`, "ok");
        }
      } catch (err) {
        setStatus("Falha na comunicação com o servidor.", "erro");
      } finally {
        btnTrans.disabled = false;
      }
    }

    async function copiar() {
      const texto = output.value;
      if (!texto) return;
      await navigator.clipboard.writeText(texto);
      copiedBadge.classList.add("visible");
      setTimeout(() => copiedBadge.classList.remove("visible"), 2000);
    }

    function setStatus(msg, tipo) {
      statusEl.innerHTML = msg;
      statusEl.className = "status " + tipo;
    }
  </script>
</body>
</html>"""


def extrair_video_id(url: str) -> str:
    padrao = r"(?:v=|youtu\.be/|shorts/|live/)([a-zA-Z0-9_-]{11})"
    match = re.search(padrao, url)
    if not match:
        raise ValueError("URL do YouTube inválida ou não reconhecida.")
    return match.group(1)


def carregar_cookies() -> dict:
    cookies = {}
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
    conteudo = ""
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()
    else:
        conteudo = os.environ.get("YOUTUBE_COOKIES", "")
    for linha in conteudo.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = linha.split("\t")
        if len(partes) >= 7:
            cookies[partes[5]] = partes[6]
    return cookies


def buscar_transcript(video_id: str, cookies: dict) -> list:
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    resp = session.get(f"https://www.youtube.com/watch?v={video_id}", timeout=20)
    resp.raise_for_status()

    match = re.search(r'"captionTracks":(\[.+?\])', resp.text)
    if not match:
        blocked = ["Sign in to confirm", "Faça login", "accounts.google.com", "consent.youtube"]
        if any(s in resp.text[:5000] for s in blocked):
            raise Exception("YouTube bloqueou a requisição. Atualize os cookies.")
        raise Exception("Nenhuma legenda encontrada para este vídeo.")

    tracks = json.loads(match.group(1))
    if not tracks:
        raise Exception("Nenhuma faixa de legenda disponível.")

    chosen = None
    for lang_prefix in ["pt", "en"]:
        for t in tracks:
            if t.get("languageCode", "").startswith(lang_prefix):
                chosen = t
                break
        if chosen:
            break
    if not chosen:
        chosen = tracks[0]

    cap_resp = session.get(chosen["baseUrl"] + "&fmt=json3", timeout=20)
    cap_resp.raise_for_status()

    lines = []
    for ev in cap_resp.json().get("events", []):
        text = "".join(s.get("utf8", "") for s in ev.get("segs", [])).strip()
        if text and text != "\n":
            lines.append(html_module.unescape(text))

    return lines


@app.route("/")
def index():
    return INDEX_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    dados = request.get_json(silent=True) or {}
    url = dados.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL não informada."}), 400

    try:
        video_id = extrair_video_id(url)
        cookies = carregar_cookies()
        linhas = buscar_transcript(video_id, cookies)
        return jsonify({"transcript": "\n".join(linhas), "video_id": video_id})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar transcrição: {str(e)}"}), 500
