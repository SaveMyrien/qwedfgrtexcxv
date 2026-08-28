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
        xbmc.log(f"[GnulaHD] Error unpacker: {e}", xbmc.LOGERROR)
        return {}

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

def extract_year_from_post(post):
    post_year = str(post.get("year", "")).strip()
    if post_year.isdigit() and len(post_year) == 4:
        return post_year

    raw_title = post.get("title", "")
    match = re.search(r'\((\d{4})\)', raw_title)
    if match:
        return match.group(1)

    release_date = str(post.get("release_date", "")).strip()
    if len(release_date) >= 4 and release_date[:4].isdigit():
        return release_date[:4]

    return ""

def find_best_post_match(posts, search_title, target_year=""):
    if not posts:
        return None

    clean_target = normalize_string(search_title)
    clean_target_tokens = clean_target.replace(" ", "")
    target_year = str(target_year).strip()

    # Filtro excluyente por tipo Película
    pelis_only = [p for p in posts if p.get("type", "").lower() in ("pelicula", "peliculas", "movie")]
    pool = pelis_only if pelis_only else posts

    # 1. Búsqueda con año especificado (Filtro estricto)
    if target_year:
        # Match exacto de tokens + año
        for post in pool:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            if clean_target_tokens == p_clean.replace(" ", "") and p_year == target_year:
                return post

        # Match de frase completa contenida + año
        for post in pool:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            pattern = rf'\b{re.escape(clean_target)}\b'
            if re.search(pattern, p_clean) and p_year == target_year:
                return post

        # Si había año y no coincidió con ningún resultado, se descarta
        return None

    # 2. Búsqueda sin año especificado
    for post in pool:
        p_clean = normalize_string(post.get("title", ""))
        if clean_target_tokens == p_clean.replace(" ", ""):
            return post

    for post in pool:
        p_clean = normalize_string(post.get("title", ""))
        pattern = rf'^{re.escape(clean_target)}$'
        if re.search(pattern, p_clean):
            return post

    for post in pool:
        p_clean = normalize_string(post.get("title", ""))
        pattern = rf'\b{re.escape(clean_target)}\b'
        if re.search(pattern, p_clean):
            return post

    return None

def find_best_series_match(posts, search_title, target_year=""):
    return find_best_post_match(posts, search_title, target_year)

def get_catalog(post_type="Pelicula", page=1):
    req_url = f"{API_SEARCH}?q=&type={post_type}&page={page}"
    try:
        res = HTTP_SESSION.get(req_url, headers=HEADERS_DEFAULT, timeout=5, verify=False)
        return res.json().get("results", [])
    except Exception as e:
        xbmc.log(f"[GnulaHD] Error catálogo: {e}", xbmc.LOGERROR)
        return []

def build_search_variations(raw_title):
    variations = []
    base_title = (raw_title or "").strip()

    if not base_title:
        return variations

    def add(v):
        v = (v or "").strip()
        if v and len(v) >= 3 and v not in variations:
            variations.append(v)

    # 1. Título completo prioritario
    add(base_title)

    # 2. Partes principales por separadores
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

    # 3. Frases largas (solo combinaciones de al menos 3 palabras)
    words = base_title.split()
    if len(words) >= 3:
        for n in range(len(words) - 1, 2, -1):
            add(" ".join(words[:n]))

    return variations

def resolve_movie(title, year="", log_dict=None, preferred_lang="latino"):
    search_queries = build_search_variations(title)
    posts = []
    search_attempts_log = []

    if log_dict is not None:
        log_dict["GNULA_SEARCH_VARIATIONS"] = search_queries

    for idx, q in enumerate(search_queries, start=1):
        search_url = f"{API_SEARCH}?q={urllib.parse.quote(q)}"

        attempt_info = {
            "intento": idx,
            "query_usada": q,
            "url": search_url,
            "http_status": None,
            "posts_encontrados": 0,
            "titulos_devueltos": [],
            "match_encontrado": False,
            "error": None
        }

        try:
            res = HTTP_SESSION.get(search_url, headers=HEADERS_DEFAULT, timeout=4, verify=False)
            attempt_info["http_status"] = res.status_code

            fetched_posts = res.json().get("results", [])
            attempt_info["posts_encontrados"] = len(fetched_posts)
            attempt_info["titulos_devueltos"] = [
                f"{p.get('title', '?')} ({p.get('year', '?')})"
                for p in fetched_posts
            ]

            if fetched_posts:
                posts.extend(fetched_posts)
                match_early = find_best_post_match(fetched_posts, title, year)
                if match_early:
                    attempt_info["match_encontrado"] = True
                    attempt_info["match_titulo"] = match_early.get("title", "")
                    attempt_info["match_url"] = match_early.get("url", "")
                    posts = [match_early]
                    search_attempts_log.append(attempt_info)
                    break
        except Exception as e:
            attempt_info["error"] = str(e)
            xbmc.log(f"[GnulaHD] Error búsqueda película: {e}", xbmc.LOGERROR)

        search_attempts_log.append(attempt_info)

    if log_dict is not None:
        log_dict["GNULA_SEARCH_ATTEMPTS"] = search_attempts_log

    selected_post = find_best_post_match(posts, title, year)
    if not selected_post:
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = "find_best_post_match (ningún post matcheó título/año)"
        return None, None

    movie_page_url = selected_post.get("url")
    if log_dict is not None:
        log_dict["GNULA_SELECTED_POST_TITLE"] = selected_post.get("title", "")
        log_dict["GNULA_SELECTED_POST_URL"] = movie_page_url

    try:
        res_page = HTTP_SESSION.get(movie_page_url, headers=HEADERS_DEFAULT, timeout=5, verify=False)
        if res_page.status_code != 200:
            if log_dict is not None:
                log_dict["GNULA_FALLO_EN"] = f"Ficha HTTP {res_page.status_code}"
            return None, None
        html_content = res_page.text
    except Exception as e:
        xbmc.log(f"[GnulaHD] Error obteniendo HTML: {e}", xbmc.LOGERROR)
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = f"Error HTML: {e}"
        return None, None

    pid, tok, vd_auth = extract_player_tokens_from_html(html_content)
    if not pid or not tok:
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = "no se encontraron _gnrdPid o _gnrdTok"
        return None, None

    player_url = f"{API_PLAYER}?id={pid}&t={tok}"
    if log_dict is not None:
        log_dict["GNULA_PLAYER_URL"] = player_url

    try:
        player_headers = HEADERS_DEFAULT.copy()
        player_headers["Referer"] = movie_page_url
        res_player = HTTP_SESSION.get(player_url, headers=player_headers, timeout=4, verify=False)
        if log_dict is not None:
            log_dict["GNULA_PLAYER_HTTP_STATUS"] = res_player.status_code
        player_json = res_player.json()
    except Exception as e:
        xbmc.log(f"[GnulaHD] Error API Player: {e}", xbmc.LOGERROR)
        if log_dict is not None:
            log_dict["GNULA_PLAYER_ERROR"] = str(e)
            log_dict["GNULA_FALLO_EN"] = "error al consultar API Player"
        return None, None

    packed_payload = player_json.get("p", "")
    unpacked_data = gnrd_unpack(packed_payload)
    langs = unpacked_data.get("langs", [])

    if not langs:
        if log_dict is not None:
            log_dict["GNULA_FALLO_EN"] = "sin datos de servidores tras desempaquetar"
        return None, None

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
        log_dict["GNULA_SERVIDORES_ENCONTRADOS"] = [
            {"src": s.get("src", ""), "name": s.get("name", "")} for s in servers
        ]

    for candidate_server in servers:
        stream_url, ref = resolve_server_stream(candidate_server, movie_page_url, vd_auth)
        if stream_url:
            return stream_url, ref

    if log_dict is not None:
        log_dict["GNULA_FALLO_EN"] = "no se pudo resolver stream de los servidores disponibles"

    return None, None

def resolve_series(query_candidates, s_num, e_num, effective_year="", preferred_lang="latino"):
    expanded_candidates = []
    for cand in query_candidates:
        vars_cand = build_search_variations(cand)
        for v in vars_cand:
            if v not in expanded_candidates:
                expanded_candidates.append(v)

    series_post = None
    used_query = expanded_candidates[0] if expanded_candidates else ""

    for candidate_query in expanded_candidates:
        search_url = f"{API_SEARCH}?q={urllib.parse.quote(candidate_query)}"
        try:
            res = HTTP_SESSION.get(search_url, headers=HEADERS_DEFAULT, timeout=4, verify=False)
            posts = res.json().get("results", [])
        except Exception:
            posts = []

        match = find_best_series_match(posts, candidate_query, effective_year)
        if match:
            series_post = match
            used_query = candidate_query
            break

    if not series_post:
        return None, None, used_query

    series_url = series_post.get("url")
    episode_page_url = None

    try:
        res_series = HTTP_SESSION.get(series_url, headers=HEADERS_DEFAULT, timeout=5, verify=False)
        if res_series.status_code == 200:
            series_html = res_series.text
            ep_pattern = rf'href=["\'](https?://[^"\']*(?:temporada-{s_num}-capitulo-{e_num}|{s_num}x{e_num}|season-{s_num}-episode-{e_num})[^"\']*)["\']'
            ep_match = re.search(ep_pattern, series_html, re.I)
            if ep_match:
                episode_page_url = ep_match.group(1)
            else:
                ep_data_match = re.search(rf'data-season=["\']?{s_num}["\']?\s+data-episode=["\']?{e_num}["\']?[^>]*data-id=["\']?(\d+)["\']?', series_html)
                if ep_data_match:
                    episode_page_url = f"{series_url}?id={ep_data_match.group(1)}"
    except Exception as e:
        xbmc.log(f"[GnulaHD] Error cargando ficha serie: {e}", xbmc.LOGERROR)

    target_page = episode_page_url if episode_page_url else series_url

    try:
        res_ep = HTTP_SESSION.get(target_page, headers=HEADERS_DEFAULT, timeout=5, verify=False)
        if res_ep.status_code != 200:
            return None, None, used_query
        ep_html = res_ep.text
    except Exception:
        return None, None, used_query

    pid, tok, vd_auth = extract_player_tokens_from_html(ep_html)
    if not pid or not tok:
        return None, None, used_query

    player_url = f"{API_PLAYER}?id={pid}&t={tok}"
    try:
        player_headers = HEADERS_DEFAULT.copy()
        player_headers["Referer"] = target_page
        res_player = HTTP_SESSION.get(player_url, headers=player_headers, timeout=4, verify=False)
        player_json = res_player.json()
    except Exception:
        return None, None, used_query

    unpacked_data = gnrd_unpack(player_json.get("p", ""))
    langs = unpacked_data.get("langs", [])
    if not langs:
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
    for candidate_server in servers:
        stream_url, ref = resolve_server_stream(candidate_server, target_page, vd_auth)
        if stream_url:
            return stream_url, ref, used_query

    return None, None, used_query
