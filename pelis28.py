# -*- coding: utf-8 -*-
import re
import urllib.parse
import json
import uuid
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://ver.pelis28.net"

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://ver.pelis28.net/",
    "Origin": "https://ver.pelis28.net",
    "Cache-Control": "no-cache"
}

def clean_url(url):
    if not url:
        return None
    url = url.strip().replace("\\/", "/")
    url = re.sub(r'["\'\\].*$', '', url)
    return url.replace('&amp;', '&')

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
    except Exception:
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
            info_url = f"https://anal.vimeos.net/info?site=pelis28.net&uuid={random_uuid}&ts={ts_now}&isIframe=false&parentUrl={urllib.parse.quote(target_url)}"
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

    except Exception:
        pass

    return None, None

def resolver_reproductor(embed_url, referer_page):
    if not embed_url:
        return None
    
    if embed_url.startswith("//"):
        embed_url = "https:" + embed_url

    if not embed_url.startswith("http"):
        return None

    if "admin-ajax.php" in embed_url or "action=doo_player_ajax" in embed_url:
        try:
            parsed = urllib.parse.urlparse(embed_url)
            qs = urllib.parse.parse_qs(parsed.query)
            post_id = qs.get("post", [""])[0]
            nume = qs.get("nume", [""])[0]
            player_type = qs.get("type", ["movie"])[0]

            ajax_url = f"{BASE_URL}/wp-admin/admin-ajax.php"
            data = {
                "action": "doo_player_ajax",
                "post": post_id,
                "nume": nume,
                "type": player_type
            }
            headers_ajax = dict(HEADERS_DEFAULT)
            headers_ajax["Referer"] = referer_page
            headers_ajax["X-Requested-With"] = "XMLHttpRequest"

            res_ajax = requests.post(ajax_url, data=data, headers=headers_ajax, timeout=10, verify=False)
            if res_ajax.status_code == 200:
                resp_json = res_ajax.json()
                embed_html = resp_json.get("embed_url", "")
                m_src = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', embed_html)
                if m_src:
                    return m_src.group(1)
                if embed_html.startswith("http"):
                    return embed_html
        except Exception:
            pass

    return embed_url

def extract_pelis28_movie_stream(query_title, target_year="", log_dict=None):
    if not query_title:
        return None, None, False

    search_term = query_title.strip()
    if "&" in search_term or "&amp;" in search_term:
        clean_cut = search_term.replace("&amp;", "&")
        search_term = clean_cut.split("&")[0].strip()

    url_search = f"{BASE_URL}/?s={urllib.parse.quote(search_term)}"
    if log_dict is not None:
        log_dict["PELIS28_SEARCH_URL"] = url_search

    try:
        res = requests.get(url_search, headers=HEADERS_DEFAULT, timeout=12, verify=False)
        if res.status_code != 200:
            if log_dict is not None:
                log_dict["PELIS28_ERROR"] = f"HTTP_{res.status_code}"
            return None, None, False
        html_search = res.text
    except Exception as e:
        if log_dict is not None:
            log_dict["PELIS28_EXCEPTION"] = str(e)
        return None, None, False

    pattern_card = r'<div class="result-item">[\s\S]*?<a href="([^"]+)"[\s\S]*?<div class="title"><a[^>]*>([^<]+)</a></div>[\s\S]*?<span class="year">(\d{4})</span>'
    matches = re.findall(pattern_card, html_search)

    if not matches:
        pattern_simple = r'<div class="title"><a href="([^"]+)">([^<]+)</a></div>[\s\S]*?<span class="year">(\d{4})</span>'
        matches = [(m[0], m[1], m[2]) for m in re.findall(pattern_simple, html_search)]

    if not matches:
        if log_dict is not None:
            log_dict["PELIS28_ERROR"] = "SIN_RESULTADOS"
        return None, None, False

    selected_url = None
    for link, name, year in matches:
        if target_year and str(year).strip() == str(target_year).strip():
            selected_url = link
            break

    if not selected_url:
        selected_url = matches[0][0]

    if log_dict is not None:
        log_dict["PELIS28_MOVIE_URL"] = selected_url

    try:
        res_movie = requests.get(selected_url, headers=HEADERS_DEFAULT, timeout=12, verify=False)
        if res_movie.status_code != 200:
            return None, None, False
        html_movie = res_movie.text
    except Exception:
        return None, None, False

    # Extraer las opciones de reproductor para validar si tienen HD
    options_tags = re.findall(r"<li[^>]*class=['\"][^'\"]*dooplay_player_option[^'\"]*['\"][^>]*>[\s\S]*?<span class=['\"]title['\"]>([^<]+)</span>", html_movie)
    valid_titles = []
    for opt_t in options_tags:
        t_clean = opt_t.strip().upper()
        if "TRAILER" not in t_clean:
            valid_titles.append(t_clean)

    # Si dice 'LATINO HD' o cualquier opción incluye 'HD', is_cam es False
    is_cam = False
    if valid_titles:
        has_hd = any("HD" in t for t in valid_titles)
        if not has_hd and any("LATINO" in t for t in valid_titles):
            is_cam = True

    if log_dict is not None:
        log_dict["PELIS28_IS_CAM"] = is_cam
        log_dict["PELIS28_OPTIONS_TITLES"] = valid_titles

    raw_embeds = []
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html_movie, re.IGNORECASE)
    for ifr in iframes:
        if ifr not in raw_embeds:
            raw_embeds.append(ifr)

    ajax_elements = re.findall(r'data-post=["\'](\d+)["\'][^>]+data-nume=["\'](\d+|opt\d+)["\']', html_movie)
    for p_id, num in ajax_elements:
        ajax_link = f"{BASE_URL}/wp-admin/admin-ajax.php?action=doo_player_ajax&post={p_id}&nume={num}&type=movie"
        if ajax_link not in raw_embeds:
            raw_embeds.append(ajax_link)

    opciones_dooplay = re.findall(r'<li[^>]+id=["\']player-option-(\d+)["\'][^>]+data-post=["\'](\d+)["\'][^>]+data-nume=["\'](\d+)["\']', html_movie)
    for opt, p_id, num in opciones_dooplay:
        ajax_link = f"{BASE_URL}/wp-admin/admin-ajax.php?action=doo_player_ajax&post={p_id}&nume={num}&type=movie"
        if ajax_link not in raw_embeds:
            raw_embeds.append(ajax_link)

    vimeos_embeds = []
    for item_url in raw_embeds:
        resuelto = resolver_reproductor(item_url, selected_url)
        if resuelto and "vimeos" in resuelto.lower():
            resuelto = clean_url(resuelto)
            if resuelto not in vimeos_embeds:
                vimeos_embeds.append(resuelto)

    if log_dict is not None:
        log_dict["PELIS28_VIMEOS_EMBEDS"] = vimeos_embeds

    for emb in vimeos_embeds:
        m3u8_url, referer_host = extract_vimeos_cdn_stream(emb)
        if m3u8_url:
            return m3u8_url, referer_host, is_cam

    return None, None, is_cam
