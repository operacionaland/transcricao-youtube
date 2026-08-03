export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return jsonResp({ error: "JSON inválido" }, 400);
    }

    const { video_id, cookie } = body;
    if (!video_id || !/^[a-zA-Z0-9_-]{11}$/.test(video_id)) {
      return jsonResp({ error: "video_id inválido" }, 400);
    }

    try {
      const html  = await fetchPage(video_id, cookie || "");
      const track = chooseBestTrack(extractTracks(html));
      const lines = await fetchTranscript(track.baseUrl, video_id, cookie || "");
      return jsonResp({ transcript: lines.join("\n"), video_id, lang: track.languageCode });
    } catch (err) {
      return jsonResp({ error: err.message }, 500);
    }
  }
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function jsonResp(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}

async function fetchPage(video_id, cookieStr) {
  const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
  };
  if (cookieStr) headers["Cookie"] = cookieStr;

  for (let attempt = 0; attempt < 3; attempt++) {
    const r = await fetch(`https://www.youtube.com/watch?v=${video_id}`, { headers });
    if (r.status === 429) {
      await sleep(1500 * (attempt + 1));
      continue;
    }
    if (!r.ok) throw new Error(`YouTube HTTP ${r.status}`);
    return r.text();
  }
  throw new Error("YouTube está limitando requisições. Tente novamente em instantes.");
}

function extractTracks(html) {
  const m = html.match(/"captionTracks":(\[.+?\])/);
  if (!m) {
    const blocked = ["Sign in to confirm", "Faça login"].some(s => html.includes(s));
    throw new Error(blocked ? "Vídeo exige login" : "Nenhuma legenda disponível para este vídeo");
  }
  const tracks = JSON.parse(m[1]);
  if (!tracks.length) throw new Error("Nenhuma faixa de legenda encontrada");
  return tracks;
}

function chooseBestTrack(tracks) {
  for (const prefix of ["pt", "en"]) {
    const t = tracks.find(t => t.languageCode && t.languageCode.startsWith(prefix));
    if (t) return t;
  }
  return tracks[0];
}

async function fetchTranscript(baseUrl, video_id, cookieStr) {
  const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Referer": `https://www.youtube.com/watch?v=${video_id}`,
  };
  if (cookieStr) headers["Cookie"] = cookieStr;

  const r = await fetch(baseUrl + "&fmt=json3", { headers });
  if (!r.ok) throw new Error(`Legenda HTTP ${r.status}`);
  const data = await r.json();
  const lines = [];
  for (const ev of data.events || []) {
    const text = (ev.segs || []).map(s => s.utf8 || "").join("").trim().replace(/\n/g, " ");
    if (text) lines.push(text);
  }
  if (!lines.length) throw new Error("Legenda baixada mas sem conteúdo");
  return lines;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
