# -*- coding: utf-8 -*-
import sys
import re
import urllib.parse
import html
import uuid
import time
import requests
import urllib3
import xbmc

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE_URL = "https://lamovie.org"
API_SEARCH = f"{API_BASE_URL}/wp-api/v1/search"
API_EPISODES = f"{API_BASE_URL}/wp-api/v1/single/episodes/list"
API_PLAYER = f"{API_BASE_URL}/wp-api/v1/player"

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://lamovie.org/",
    "Origin": "https://lamovie.org",
    "Cache-Control": "no-cache"
}

def sanitize_m3u8_url(url):
    if not url:
        return None
    clean = url.strip()
    clean = re.sub(r'["\'\\].*$', '', clean)
    clean = clean.replace('&amp;', '&')
    return clean

def verificar_stream_online(m3u8_url, referer_host=None):
    if not m3u8_url or not m3u8_url.startswith("http"):
        return False
    try:
        parsed = urllib.parse.urlparse(m3u8_url)
        origin_val = f"{parsed.scheme}://{parsed.netloc}"
        ref_val = referer_host if referer_host else f"{origin_val}/"

        headers = {
            "User-Agent": HEADERS_DEFAULT["User-Agent"],
            "Referer": ref_val,
            "Origin": origin_val
        }
        res = requests.get(m3u8_url, headers=headers, timeout=3.5, verify=False)
        if res.status_code == 200 and ("#EXTM3U" in res.text or "#EXT-X-" in res.text):
            return True
    except Exception:
        pass
    return False

def unpack_dean_edwards_js_exact(packed_code):
    try:
        packer_match = re.search(r"eval\(function\(p,a,c,k,e,d\)[\s\S]*?\.split\('\|'\)\)\)", packed_code)
        if not packer_match:
            return ""

        code = packer_match.group(0)
        args_match = re.search(r"}\s*\(\s*'(.*?)'\s*,\s*(\d+)\s*,\s*(\d+)\s*,'(.*?)'\.split\('\|'\)", code, re.DOTALL)
        if not args_match:
            return ""

        p, a, c, k = args_match.groups()
        a = int(a)
        c = int(c)
        k = k.split('|')

        def base36_encode(number):
            alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'
            base36 = ''
            while number:
                number, i = divmod(number, 36)
                base36 = alphabet[i] + base36
            return base36 or '0'

        def e(c_val):
            prefix = '' if c_val < a else e(int(c_val / a))
            remainder = c_val % a
            suffix = chr(remainder + 29) if remainder > 35 else base36_encode(remainder)
            return prefix + suffix

        while c > 0:
            c -= 1
            if c < len(k) and k[c]:
                token = e(c)
                pattern = r'\b' + re.escape(token) + r'\b'
                p = re.sub(pattern, k[c], p)

        return p
    except Exception as err:
        xbmc.log(f"[LaMovie] Error unpacker: {err}", xbmc.LOGERROR)
        return ""

def extract_vimeos_cdn_stream(embed_url):
    try:
        if not embed_url:
            return None, None

        target_url = embed_url
        if target_url.startswith("//"):
            target_url = "https:" + target_url

        session = requests.Session()
        res_embed = session.get(target_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
        if res_embed.status_code != 200:
            return None, None

        html_text = res_embed.text

        try:
            random_uuid = str(uuid.uuid4())
            ts_now = int(time.time())
            info_url = f"https://anal.vimeos.net/info?site=lamovie.link&uuid={random_uuid}&ts={ts_now}&isIframe=false&parentUrl={urllib.parse.quote(target_url)}"
            headers_info = dict(HEADERS_DEFAULT)
            headers_info["Referer"] = target_url
            headers_info["Origin"] = "https://vimeos.net"
            session.get(info_url, headers=headers_info, timeout=5, verify=False)
        except Exception:
            pass

        unpacked_js = unpack_dean_edwards_js_exact(html_text)
        raw_m3u8 = None
        if unpacked_js:
            file_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', unpacked_js, re.I)
            if file_match and file_match.group(1):
                raw_m3u8 = file_match.group(1)

            if not raw_m3u8:
                token_match = re.search(r'(https?://[^\s"\'<>\\]+?\.m3u8\?[^\s"\'<>\\]+)', unpacked_js, re.I)
                if token_match and token_match.group(1):
                    raw_m3u8 = token_match.group(1)

            if not raw_m3u8:
                simple_match = re.search(r'(https?://[^\s"\'<>\\]+?\.m3u8)', unpacked_js, re.I)
                if simple_match and simple_match.group(1):
                    raw_m3u8 = simple_match.group(1)

        if not raw_m3u8:
            html_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html_text, re.I) or \
                         re.search(r'(https?://[^\s"\'<>\\]+?\.m3u8\?[^\s"\'<>\\]+)', html_text, re.I)
            if html_match and html_match.group(1):
                raw_m3u8 = html_match.group(1)

        clean_master = sanitize_m3u8_url(raw_m3u8)
        if not clean_master:
            return None, None

        pattern_urlset = r'(/hls2/\d+/\d+/)([a-zA-Z0-9]+)_,?([a-zA-Z0-9,]*),?\.urlset/master\.m3u8(\?.*)?'
        match_u = re.search(pattern_urlset, clean_master)

        if match_u:
            base_path = match_u.group(1)
            file_id = match_u.group(2)
            qualities_str = match_u.group(3)
            query_raw = (match_u.group(4) or "").lstrip("?")

            parsed_master = urllib.parse.urlparse(clean_master)
            server_match = re.search(r'^(s\d+)\.', parsed_master.netloc)
            server_id = server_match.group(1) if server_match else "s11"

            q_params = urllib.parse.parse_qs(query_raw)
            if "srv" not in q_params:
                q_params["srv"] = [server_id]

            final_query = urllib.parse.urlencode(q_params, doseq=True)

            qualities = [q for q in qualities_str.split(',') if q]
            priority_order = ['x', 'h', 'n', 'l']
            selected_quality = 'h'
            for q_candidate in priority_order:
                if q_candidate in qualities:
                    selected_quality = q_candidate
                    break

            cdn_hosts = [
                f"{parsed_master.scheme}://{parsed_master.netloc}",
                "https://p3.vimeos.zip",
                "https://p2.vimeos.zip",
                "https://p4.vimeos.zip",
                "https://p6.vimeos.zip",
                "https://p1.vimeos.zip"
            ]

            for host in cdn_hosts:
                candidate_url = f"{host}{base_path}{file_id}_{selected_quality}/index-v1-a1.m3u8?{final_query}"
                if verificar_stream_online(candidate_url, target_url):
                    return candidate_url, target_url

            fallback_url = f"https://p3.vimeos.zip{base_path}{file_id}_{selected_quality}/index-v1-a1.m3u8?{final_query}"
            if verificar_stream_online(fallback_url, target_url):
                return fallback_url, target_url

        if verificar_stream_online(clean_master, target_url):
            return clean_master, target_url

    except Exception as err:
        xbmc.log(f"[LaMovie] Error extraccion vimeos: {err}", xbmc.LOGERROR)

    return None, None

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
    raw_title = post.get("title", "")
    match = re.search(r'\((\d{4})\)', raw_title)
    if match:
        return match.group(1)

    release_date = str(post.get("release_date", "")).strip()
    if len(release_date) >= 4 and release_date[:4].isdigit():
        return release_date[:4]

    post_year = str(post.get("year", "")).strip()
    if post_year.isdigit() and len(post_year) == 4:
        return post_year

    return ""

def find_best_post_match(posts, search_title, target_year=""):
    if not posts:
        return None

    clean_target = normalize_string(search_title)
    clean_target_tokens = clean_target.replace(" ", "")
    target_year = str(target_year).strip()

    first_keyword = clean_target.split()[0] if clean_target else ""

    subtitles = []
    if ":" in search_title:
        sub_part = normalize_string(search_title.split(":", 1)[1])
        if sub_part:
            subtitles.append(sub_part)
    if " - " in search_title:
        sub_part = normalize_string(search_title.split(" - ", 1)[1])
        if sub_part:
            subtitles.append(sub_part)

    if target_year:
        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            if clean_target_tokens == p_clean.replace(" ", "") and p_year == target_year:
                return post

        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            for sub in subtitles:
                if sub and (sub in p_clean or p_clean in sub) and p_year == target_year:
                    return post

        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            if first_keyword and first_keyword in p_clean.split() and p_year == target_year:
                return post

        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            pattern = rf'\b{re.escape(clean_target)}\b'
            if re.search(pattern, p_clean) and p_year == target_year:
                return post

    for post in posts:
        p_clean = normalize_string(post.get("title", ""))
        p_year = extract_year_from_post(post)
        if target_year and p_year and p_year != target_year:
            continue
        if clean_target_tokens == p_clean.replace(" ", ""):
            return post
        for sub in subtitles:
            if sub and (sub in p_clean or p_clean in sub):
                return post
        if first_keyword and first_keyword in p_clean.split():
            return post

    return None

def find_best_series_match(posts, search_title, target_year=""):
    if not posts:
        return None

    clean_target = normalize_string(search_title)
    clean_target_tokens = clean_target.replace(" ", "")
    target_year = str(target_year).strip()
    first_keyword = clean_target.split()[0] if clean_target else ""

    subtitles = []
    if ":" in search_title:
        sub_part = normalize_string(search_title.split(":", 1)[1])
        if sub_part:
            subtitles.append(sub_part)
    if " - " in search_title:
        sub_part = normalize_string(search_title.split(" - ", 1)[1])
        if sub_part:
            subtitles.append(sub_part)

    if target_year:
        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            if clean_target_tokens == p_clean.replace(" ", "") and p_year == target_year:
                return post

        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            for sub in subtitles:
                if sub and (sub in p_clean or p_clean in sub) and p_year == target_year:
                    return post

        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            if first_keyword and first_keyword in p_clean.split() and p_year == target_year:
                return post

        pattern = rf'\b{re.escape(clean_target)}\b'
        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            if re.search(pattern, p_clean) and p_year == target_year:
                return post

        return None

    for post in posts:
        p_clean = normalize_string(post.get("title", ""))
        if clean_target_tokens == p_clean.replace(" ", ""):
            return post
        for sub in subtitles:
            if sub and (sub in p_clean or p_clean in sub):
                return post
        if first_keyword and first_keyword in p_clean.split():
            return post

    pattern = rf'\b{re.escape(clean_target)}\b'
    for post in posts:
        p_clean = normalize_string(post.get("title", ""))
        if re.search(pattern, p_clean):
            return post

    return None

def get_episode_post_id(series_id, season_num, episode_num):
    page = 1
    target_season = int(season_num)
    target_episode = int(episode_num)

    while True:
        episodes_url = f"{API_EPISODES}?_id={series_id}&season={target_season}&page={page}&postsPerPage=15"
        try:
            res = requests.get(episodes_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
            data = res.json().get("data", {})
            episodes = data.get("posts", [])
            pagination = data.get("pagination", {})
        except Exception as e:
            xbmc.log(f"[LaMovie] Error lista episodios: {e}", xbmc.LOGERROR)
            break

        if not episodes:
            break

        for ep in episodes:
            s_num = int(ep.get("season_number", 0))
            e_num = int(ep.get("episode_number", 0))
            if s_num == target_season and e_num == target_episode:
                return ep.get("_id")

        last_page = int(pagination.get("last_page", 1))
        if page >= last_page:
            break
        page += 1

    return None

def resolve_series_from_year_catalog(target_year):
    req_url = f"{API_SEARCH}?filter=%7B%7D&postType=any&postsPerPage=30"
    try:
        res = requests.get(req_url, headers=HEADERS_DEFAULT, timeout=8, verify=False)
        posts = res.json().get("data", {}).get("posts", [])
        for post in posts:
            p_year = extract_year_from_post(post)
            if str(target_year).strip() == p_year:
                raw = post.get("title", "").split("(")[0].strip()
                if raw:
                    return raw
    except Exception:
        pass
    return ""

def get_catalog(post_type="movies", page=1):
    req_url = f"{API_SEARCH}?filter=%7B%7D&postType={post_type}&page={page}&postsPerPage=24"
    try:
        res = requests.get(req_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
        return res.json().get("data", {}).get("posts", [])
    except Exception as e:
        xbmc.log(f"[LaMovie] Error catálogo: {e}", xbmc.LOGERROR)
        return []

def build_search_variations(raw_title):
    """
    Genera variaciones de búsqueda en orden de prioridad.

    FIX: antes solo probaba "primera palabra sola" y luego el
    "título completo", saltándose combinaciones intermedias como
    "Harry Potter" (2 palabras). Ahora se agrega una progresión de
    palabras (2, 3, 4...) ANTES de caer a la palabra suelta, que es
    la variante más ruidosa y debería usarse como casi último recurso.
    También se agrega el título completo normalizado (sin tildes/
    puntuación) como red de seguridad final, por si el buscador del
    sitio es sensible a acentos.
    """
    variations = []
    base_title = raw_title.strip()

    if not base_title:
        return variations

    def add(v):
        v = (v or "").strip()
        if v and v not in variations:
            variations.append(v)

    # PRIORIDAD 1: si contiene dos puntos ':' (ej. "Spider-Man: Sin camino a casa")
    if ":" in base_title:
        part_before, part_after = base_title.split(":", 1)
        add(part_after)
        add(part_before)

    # PRIORIDAD 2: si contiene guión con espacios ' - '
    if " - " in base_title:
        part_before, part_after = base_title.split(" - ", 1)
        add(part_after)
        add(part_before)

    # PRIORIDAD 3: si contiene '&' o '&amp;'
    if "&" in base_title or "&amp;" in base_title:
        raw_cut = base_title.replace("&amp;", "&")
        add(raw_cut.split("&")[0])

    # PRIORIDAD 4 (NUEVO): progresión de palabras, de 2 en adelante.
    # Esto es lo que permite encontrar "Harry Potter" en vez de
    # saltar directo de "Harry" al título completo con subtítulo.
    words = base_title.split()
    for n in range(2, len(words)):  # deja fuera 1 palabra (va después) y el total (va al final)
        add(" ".join(words[:n]))

    # PRIORIDAD 5: primera palabra aislada (ahora es fallback, no el primer intento)
    if words:
        add(words[0])

    # PRIORIDAD 6: título completo tal cual vino
    add(base_title)

    # PRIORIDAD 7 (NUEVO): título completo normalizado, sin tildes ni
    # puntuación, como último recurso si el buscador del sitio no
    # matchea bien con acentos/símbolos.
    normalized_full = normalize_string(base_title)
    if normalized_full:
        add(normalized_full.title())

    return variations

def resolve_movie(title, year="", log_dict=None):
    """
    log_dict: diccionario opcional (el mismo que arma core.py) donde se
    va acumulando el detalle de cada intento de búsqueda, para poder
    ver en el log remoto exactamente qué URL se pegó, qué devolvió la
    API y en qué paso falló.
    """
    search_queries = build_search_variations(title)
    posts = []

    # Acá se guarda, intento por intento, todo lo relevante para debug.
    search_attempts_log = []

    if log_dict is not None:
        log_dict["LAMOVIE_SEARCH_VARIATIONS"] = search_queries

    for idx, q in enumerate(search_queries, start=1):
        # postsPerPage subido de 20 a 30: no se pagina, pero cubre
        # el caso de hasta ~25-30 títulos parecidos en una sola
        # respuesta, que es el techo que se espera para este catálogo.
        search_url = f"{API_SEARCH}?filter=%7B%7D&postType=any&q={urllib.parse.quote_plus(q)}&postsPerPage=30"

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
            res = requests.get(search_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
            attempt_info["http_status"] = res.status_code

            fetched_posts = res.json().get("data", {}).get("posts", [])
            attempt_info["posts_encontrados"] = len(fetched_posts)
            # Guardamos título + año de cada post devuelto, para ver a
            # simple vista si la película que buscás aparece en la
            # respuesta cruda de la API, aunque el matcher no la elija.
            attempt_info["titulos_devueltos"] = [
                f"{p.get('title', '?')} ({extract_year_from_post(p) or '?'})"
                for p in fetched_posts
            ]

            if fetched_posts:
                posts.extend(fetched_posts)
                match_early = find_best_post_match(posts, title, year)
                if match_early:
                    attempt_info["match_encontrado"] = True
                    attempt_info["match_titulo"] = match_early.get("title", "")
                    attempt_info["match_id"] = match_early.get("_id", "")
                    posts = [match_early]
                    search_attempts_log.append(attempt_info)
                    break
        except Exception as e:
            attempt_info["error"] = str(e)
            xbmc.log(f"[LaMovie] Error búsqueda película: {e}", xbmc.LOGERROR)

        search_attempts_log.append(attempt_info)

    if log_dict is not None:
        log_dict["LAMOVIE_SEARCH_ATTEMPTS"] = search_attempts_log

    selected_post = find_best_post_match(posts, title, year)
    if not selected_post:
        if log_dict is not None:
            log_dict["LAMOVIE_FALLO_EN"] = "find_best_post_match (ningún post matcheó título/año)"
        return None, None

    post_id = selected_post.get("_id")
    player_url = f"{API_PLAYER}?postId={post_id}&demo=0"

    if log_dict is not None:
        log_dict["LAMOVIE_SELECTED_POST_ID"] = post_id
        log_dict["LAMOVIE_SELECTED_POST_TITLE"] = selected_post.get("title", "")
        log_dict["LAMOVIE_PLAYER_URL"] = player_url

    try:
        res_player = requests.get(player_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
        if log_dict is not None:
            log_dict["LAMOVIE_PLAYER_HTTP_STATUS"] = res_player.status_code
        embeds = res_player.json().get("data", {}).get("embeds", [])
    except Exception as e:
        xbmc.log(f"[LaMovie] Error API Player película: {e}", xbmc.LOGERROR)
        embeds = []
        if log_dict is not None:
            log_dict["LAMOVIE_PLAYER_ERROR"] = str(e)

    if log_dict is not None:
        log_dict["LAMOVIE_EMBEDS_ENCONTRADOS"] = [
            {"server": e.get("server", ""), "url": e.get("url", "")} for e in embeds
        ]

    if not embeds:
        if log_dict is not None:
            log_dict["LAMOVIE_FALLO_EN"] = "sin embeds en la respuesta del player"
        return None, None

    ordered_embeds = []
    for embed in embeds:
        url = embed.get("url", "").lower()
        name = embed.get("server", "").lower()
        if "vimeos" in url or "lamovie" in name:
            ordered_embeds.insert(0, embed)
        elif "goodstream" in url or "goodstream" in name:
            ordered_embeds.append(embed)

    if not ordered_embeds:
        ordered_embeds = embeds

    embed_attempts_log = []
    for candidate_embed in ordered_embeds:
        embed_url = candidate_embed.get("url", "")
        m3u8, ref = extract_vimeos_cdn_stream(embed_url)
        embed_attempts_log.append({
            "embed_url": embed_url,
            "server": candidate_embed.get("server", ""),
            "m3u8_extraido": bool(m3u8)
        })
        if m3u8:
            if log_dict is not None:
                log_dict["LAMOVIE_EMBED_ATTEMPTS"] = embed_attempts_log
            return m3u8, ref

    if log_dict is not None:
        log_dict["LAMOVIE_EMBED_ATTEMPTS"] = embed_attempts_log
        log_dict["LAMOVIE_FALLO_EN"] = "no se pudo extraer m3u8 de ningún embed"

    return None, None

def resolve_series(query_candidates, s_num, e_num, effective_year=""):
    expanded_candidates = []
    for cand in query_candidates:
        vars_cand = build_search_variations(cand)
        for v in vars_cand:
            if v not in expanded_candidates:
                expanded_candidates.append(v)

    series_post = None
    used_query = expanded_candidates[0] if expanded_candidates else ""

    for candidate_query in expanded_candidates:
        # postsPerPage subido de 26 a 30 por la misma razón que en resolve_movie
        search_url = f"{API_SEARCH}?filter=%7B%7D&postType=any&q={urllib.parse.quote_plus(candidate_query)}&postsPerPage=30"
        try:
            res = requests.get(search_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
            posts = res.json().get("data", {}).get("posts", [])
        except Exception:
            posts = []

        match = find_best_series_match(posts, candidate_query, effective_year)
        if match:
            series_post = match
            used_query = candidate_query
            break

    if not series_post:
        return None, None, used_query

    series_id = series_post.get("_id")
    episode_id = get_episode_post_id(series_id, s_num, e_num)
    if not episode_id:
        return None, None, used_query

    player_url = f"{API_PLAYER}?postId={episode_id}&demo=0"
    try:
        res_player = requests.get(player_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
        embeds = res_player.json().get("data", {}).get("embeds", [])
    except Exception:
        embeds = []

    if not embeds:
        return None, None, used_query

    ordered_embeds = []
    for embed in embeds:
        url = embed.get("url", "").lower()
        name = embed.get("server", "").lower()
        if "vimeos" in url or "lamovie" in name:
            ordered_embeds.insert(0, embed)
        elif "goodstream" in url or "goodstream" in name:
            ordered_embeds.append(embed)

    if not ordered_embeds:
        ordered_embeds = embeds

    for candidate_embed in ordered_embeds:
        m3u8, ref = extract_vimeos_cdn_stream(candidate_embed.get("url", ""))
        if m3u8:
            return m3u8, ref, used_query

    return None, None, used_query
