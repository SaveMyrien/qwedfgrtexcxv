# -*- coding: utf-8 -*-
import sys
import re
import urllib.parse
import requests
import urllib3
import xbmc

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS_PELISPLUS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://pelisplustv.net/"
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
        headers = {
            "User-Agent": HEADERS_PELISPLUS["User-Agent"],
            "Referer": referer_host if referer_host else "https://streamfort.online/"
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
        xbmc.log(f"[Pelisplus] Error unpacker: {err}", xbmc.LOGERROR)
        return ""

def search_pelisplus_series_url(title, target_year=""):
    try:
        url_search = f"https://pelisplustv.net/search.html?keyword={urllib.parse.quote(title)}"
        res = requests.get(url_search, headers=HEADERS_PELISPLUS, timeout=10, verify=False)
        if res.status_code != 200:
            return None

        html = res.text
        patron_card = r'<a[^>]+href="([^"]+)"[^>]*>[\s\S]*?<span class="movie-badge">(\d{4})</span>[\s\S]*?</a>'
        matches = re.findall(patron_card, html)

        for path, anio in matches:
            if str(anio).strip() == str(target_year).strip() and ("/serie/" in path or "/series/" in path):
                return urllib.parse.urljoin("https://pelisplustv.net", path)

        for path, anio in matches:
            if "/serie/" in path or "/series/" in path:
                return urllib.parse.urljoin("https://pelisplustv.net", path)

        patron_series = r'href="([^"]*(?:serie|series)/[^"]+)"'
        series_links = re.findall(patron_series, html)
        if series_links:
            return urllib.parse.urljoin("https://pelisplustv.net", series_links[0])

    except Exception as e:
        xbmc.log(f"[Pelisplus] Error búsqueda: {e}", xbmc.LOGERROR)

    return None

def extract_streamfort_m3u8_from_pelisplus(series_url, s_num, e_num):
    try:
        res_series = requests.get(series_url, headers=HEADERS_PELISPLUS, timeout=10, verify=False)
        if res_series.status_code != 200:
            return None, None

        html_series = res_series.text

        patron_ep = rf'href="([^"]+temporada-{s_num}/capitulo-{e_num})"'
        match_ep = re.search(patron_ep, html_series, re.IGNORECASE)

        ep_path = None
        if match_ep:
            ep_path = match_ep.group(1)
        else:
            patron_query = rf'href="([^"]+\?season={s_num}&amp;ep={e_num}|[^"]+\?season={s_num}&ep={e_num})"'
            match_query = re.search(patron_query, html_series, re.IGNORECASE)
            if match_query:
                ep_path = match_query.group(1).replace("&amp;", "&")

        if not ep_path:
            return None, None

        ep_url = urllib.parse.urljoin("https://pelisplustv.net", ep_path)

        res_ep = requests.get(ep_url, headers=HEADERS_PELISPLUS, timeout=10, verify=False)
        if res_ep.status_code != 200:
            return None, None

        html_ep = res_ep.text

        patron_streamfort = r'(https?://streamfort\.online/e/[a-zA-Z0-9]+)'
        matches_sf = re.findall(patron_streamfort, html_ep)
        if not matches_sf:
            return None, None

        embed_sf = matches_sf[0]
        headers_sf = dict(HEADERS_PELISPLUS)
        headers_sf["Referer"] = ep_url

        res_embed = requests.get(embed_sf, headers=headers_sf, timeout=10, verify=False)
        if res_embed.status_code != 200:
            return None, None

        unpacked = unpack_dean_edwards_js_exact(res_embed.text)
        if not unpacked:
            return None, None

        m3u8_matches = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', unpacked)
        if m3u8_matches:
            stream_url = m3u8_matches[0].replace("\\/", "/")
            clean_stream = sanitize_m3u8_url(stream_url)
            if verificar_stream_online(clean_stream, embed_sf):
                return clean_stream, embed_sf

    except Exception as e:
        xbmc.log(f"[Pelisplus] Error extracción: {e}", xbmc.LOGERROR)

    return None, None

def resolve_series(query_candidates, s_num, e_num, effective_year=""):
    for candidate_query in query_candidates:
        pelisplus_url = search_pelisplus_series_url(candidate_query, effective_year)
        if pelisplus_url:
            m3u8, embed_url = extract_streamfort_m3u8_from_pelisplus(pelisplus_url, s_num, e_num)
            if m3u8:
                return m3u8, embed_url
    return None, None
