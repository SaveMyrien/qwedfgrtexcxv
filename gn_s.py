# -*- final -*-
import sys
import re
import urllib.parse
import html
import base64
import json
import requests
import urllib3
import xbmc

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE_URL = "https://ww3.gnulahd.nu"
API_SEARCH = f"{API_BASE_URL}/wp-json/gnrd/v1/search"
API_PLAYER = f"{API_BASE_URL}/wp-json/gnrd/v1/player"
VIDARA_RESOLVE = f"{API_BASE_URL}/panel/vidara-resolve.php"

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": f"{API_BASE_URL}/",
    "Origin": API_BASE_URL,
    "Cache-Control": "no-cache"
}

HTTP_SESSION = requests.Session()
HTTP_ADAPTER = requests.adapters.HTTPAdapter(pool_connections=15, pool_maxsize=15, max_retries=1)
HTTP_SESSION.mount("https://", HTTP_ADAPTER)
HTTP_SESSION.mount("http://", HTTP_ADAPTER)

def sanitize_m3u8_url(url):
    if not url:
        return None
    clean = url.strip()
    clean = re.sub(r'["\'\\].*$', '', clean)
    clean = clean.replace('&amp;', '&')
    return clean

def gnrd_unpack(packed_string):
    try:
        if not packed_string:
            return {}
        decoded_bytes = base64.b64decode(packed_string)
        key = [103, 78, 55, 100]
        unpacked_bytes = bytearray()
        for i, byte in enumerate(decoded_bytes):
            unpacked_bytes.append(byte ^ key[i & 3])
        unpacked_text = unpacked_bytes.decode('utf-8')
        return json.loads(unpacked_text)
    except Exception as e:
        xbmc.log(f"[GnulaHD Series] Error unpacker: {e}", xbmc.LOGERROR)
        return {}

def normalize_string(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'\(\d{4}\)', '', text)
    replacements = (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("Á", "a"), ("É", "e"), ("Í", "i"), ("Ó", "o"), ("Ú", "u"),
        ("ñ", "n"), ("Ñ", "n"), ("&amp;", " "), ("&", " ")
    )
    for a, b in replacements:
        text = text.replace(a, b)
    return re.sub(r'[^a-zA-Z0-9\s]', ' ', text).lower().strip()

def build_search_variations(raw_title):
    variations = []
    base_title = (raw_title or "").strip()
    if not base_title:
        return variations

    def add(v):
        v = (v or "").strip()
        if v and v not in variations:
            variations.append(v)

    # 1. Título completo siempre en primer lugar
    add(base_title)

    # 2. Subtítulos antes y después de separadores
    if ":" in base_title:
        part_before, part_after = base_title.split(":", 1)
        add(part_before)
        add(part_after)

    if " - " in base_title:
        part_before, part_after = base_title.split(" - ", 1)
        add(part_before)
        add(part_after)

    if "&" in base_title or "&amp;" in base_title:
        raw_cut = base_title.replace("&amp;", "&")
        add(raw_cut.split("&")[0])

    # 3. Frases largas compuestas
    words = base_title.split()
    for n in range(len(words) - 1, 1, -1):
        add(" ".join(words[:n]))

    return variations

def extract_year_from_post(post):
    post_year = str(post.get("year", "")).strip()
    if post_year.isdigit() and len(post_year) == 4:
        return post_year

    raw_title = post.get("title", "")
    match = re.search(r'\((\d{4})\)', raw_title)
    if match:
        return match.group(1)

    return ""

def find_best_series_match(results, search_title, target_year=""):
    if not results:
        return None

    clean_target = normalize_string(search_title)
    clean_target_tokens = clean_target.replace(" ", "")
    target_year = str(target_year).strip()

    series_only = [item for item in results if item.get("type", "").lower() in ("serie", "series", "anime")]
    pool = series_only if series_only else results

    # 1. Si hay año definido: exigir coincidencia estricta de título + año
    if target_year:
        for item in pool:
            p_clean = normalize_string(item.get("title", ""))
            p_year = extract_year_from_post(item)
            if clean_target_tokens == p_clean.replace(" ", "") and p_year == target_year:
                return item

        for item in pool:
            p_clean = normalize_string(item.get("title", ""))
            p_year = extract_year_from_post(item)
            pattern = rf'\b{re.escape(clean_target)}\b'
            if re.search(pattern, p_clean) and p_year == target_year:
                return item

        # Si el año no coincide, no forzamos coincidencias falsas
        return None

    # 2. Si no hay año: buscar coincidencia exacta de tokens o frase completa
    for item in pool:
        p_clean = normalize_string(item.get("title", ""))
        if clean_target_tokens == p_clean.replace(" ", ""):
            return item

    for item in pool:
        p_clean = normalize_string(item.get("title", ""))
        pattern = rf'^{re.escape(clean_target)}$'
        if re.search(pattern, p_clean):
            return item

    for item in pool:
        p_clean = normalize_string(item.get("title", ""))
        pattern = rf'\b{re.escape(clean_target)}\b'
        if re.search(pattern, p_clean):
            return item

    return None

def extract_player_tokens_from_html(html_text):
    pid_match = re.search(r'var\s+_gnrdPid\s*=\s*(\d+)', html_text)
    if not pid_match:
        pid_match = re.search(r'_gnrdPid\s*=\s*(\d+)', html_text)
    if not pid_match:
        pid_match = re.search(r'tsUpdateView\((\d+)\)', html_text)

    tok_match = re.search(r'_gnrdTok\s*=\s*["\']([a-f0-9]+)["\']', html_text)
    if not tok_match:
        tok_match = re.search(r'AUTH\s*=\s*["\']&t=([a-f0-9]+)["\']', html_text)

    vd_auth_match = re.search(r'VD_AUTH\s*=\s*["\']([^"\']+)["\']', html_text)

    pid = pid_match.group(1) if pid_match else None
    tok = tok_match.group(1) if tok_match else None
    vd_auth = vd_auth_match.group(1) if vd_auth_match else ""

    return pid, tok, vd_auth

def resolve_server_stream(server_obj, page_url, vd_auth=""):
    src = server_obj.get("src", "")
    if not src:
        return None, None

    vd_match = re.search(r'(vidara\.to|vidaraa\.cc)/(?:e/)?([A-Za-z0-9_-]+)', src, re.I)
    if vd_match:
        host = vd_match.group(1).lower()
        code = vd_match.group(2)
        auth_param = vd_auth if vd_auth.startswith("&") else f"&{vd_auth}" if vd_auth else ""
        vidara_url = f"{VIDARA_RESOLVE}?pl=1&code={code}&host={host}{auth_param}"
        return vidara_url, page_url

    if ".m3u8" in src or ".mp4" in src:
        return src, page_url

    return src, page_url

def build_kodi_stream_url(raw_stream_url, referer=None):
    if not raw_stream_url:
        return None
    kodi_headers = {
        "User-Agent": HEADERS_DEFAULT["User-Agent"],
        "Referer": referer if referer else f"{API_BASE_URL}/",
        "Origin": API_BASE_URL
    }
    return f"{raw_stream_url}|{urllib.parse.urlencode(kodi_headers)}"

def resolve_series(query_candidates, s_num, e_num, effective_year="", log_dict=None, preferred_lang="latino"):
    expanded_candidates = []
    for cand in query_candidates:
        vars_cand = build_search_variations(cand)
        for v in vars_cand:
            if v not in expanded_candidates:
                expanded_candidates.append(v)

    if log_dict is not None:
        log_dict["GNULA_SERIES_SEARCH_VARIATIONS"] = expanded_candidates

    series_item = None
    used_query = expanded_candidates[0] if expanded_candidates else ""

    for candidate_query in expanded_candidates:
        search_url = f"{API_SEARCH}?q={urllib.parse.quote(candidate_query)}"
        try:
            res = HTTP_SESSION.get(search_url, headers=HEADERS_DEFAULT, timeout=5, verify=False)
            if res.status_code == 200:
                results = res.json().get("results", [])
                match = find_best_series_match(results, candidate_query, effective_year)
                if match:
                    series_item = match
                    used_query = candidate_query
                    break
        except Exception as e:
            xbmc.log(f"[GnulaHD Series] Error en búsqueda con query '{candidate_query}': {e}", xbmc.LOGERROR)

    if not series_item:
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = "no se encontró la serie en el buscador con título/año válidos"
        return None, None, used_query

    series_url = series_item.get("url", "")
    slug_match = re.search(r'/(?:ver/)?([^/]+)/?$', series_url)
    slug = slug_match.group(1) if slug_match else ""

    if not slug:
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = "no se pudo extraer el slug de la serie"
        return None, None, used_query

    s_int = int(s_num)
    e_int = int(e_num)

    episode_url = f"{API_BASE_URL}/{slug}-{s_int}x{e_int:02d}/"

    if log_dict is not None:
        log_dict["GNULA_SERIES_TITLE"] = series_item.get("title", "")
        log_dict["GNULA_EPISODE_URL"] = episode_url

    try:
        ep_headers = HEADERS_DEFAULT.copy()
        ep_headers["Referer"] = f"{API_BASE_URL}/"
        res_ep = HTTP_SESSION.get(episode_url, headers=ep_headers, timeout=6, verify=False)

        if res_ep.status_code != 200:
            fallback_url = f"{API_BASE_URL}/{slug}-{s_int}x{e_int}/"
            res_ep = HTTP_SESSION.get(fallback_url, headers=ep_headers, timeout=6, verify=False)
            if res_ep.status_code == 200:
                episode_url = fallback_url
            else:
                if log_dict is not None:
                    log_dict["GNULA_FALLO_EN"] = f"Episodio HTTP {res_ep.status_code}"
                return None, None, used_query

        ep_html = res_ep.text
    except Exception as e:
        xbmc.log(f"[GnulaHD Series] Error al cargar página de episodio: {e}", xbmc.LOGERROR)
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = f"Error cargando episodio: {e}"
        return None, None, used_query

    pid, tok, vd_auth = extract_player_tokens_from_html(ep_html)
    if not pid or not tok:
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = f"no se extrajo PID o TOK del episodio ({episode_url})"
        return None, None, used_query

    player_api_url = f"{API_PLAYER}?id={pid}&t={tok}"

    try:
        player_headers = HEADERS_DEFAULT.copy()
        player_headers["Referer"] = episode_url
        res_player = HTTP_SESSION.get(player_api_url, headers=player_headers, timeout=5, verify=False)
        if res_player.status_code != 200:
            if log_dict is not None:
                log_dict["GNULA_FALLO_EN"] = f"API Player HTTP {res_player.status_code}"
            return None, None, used_query
        player_json = res_player.json()
    except Exception as e:
        xbmc.log(f"[GnulaHD Series] Error en API Player: {e}", xbmc.LOGERROR)
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = f"Error API Player: {e}"
        return None, None, used_query

    packed_payload = player_json.get("p", "")
    unpacked_data = gnrd_unpack(packed_payload)

    langs = unpacked_data.get("langs", [])
    if not langs:
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = "sin datos de idiomas en respuesta del player"
        return None, None, used_query

    chosen_lang_group = None
    for l_group in langs:
        label = l_group.get("label", "").lower()
        if preferred_lang.lower() in label:
            chosen_lang_group = l_group
            break

    if not chosen_lang_group and langs:
        chosen_lang_group = langs[0]

    servers = chosen_lang_group.get("servers", [])
    if log_dict is not None:
        log_dict["GNULA_SERIES_SERVIDORES"] = [
            {"src": s.get("src", ""), "name": s.get("name", "")} for s in servers
        ]

    for srv in servers:
        stream_url, referer = resolve_server_stream(srv, episode_url, vd_auth)
        if stream_url:
            return stream_url, referer, used_query

    if log_dict is not None:
        log_dict["GNULA_FALLO_EN"] = "no se pudo resolver stream de los servidores disponibles"

    return None, None, used_query
