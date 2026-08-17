# -*- coding: utf-8 -*-
# -*- v4 -*-
import sys
import re
import urllib.parse
import json
import requests
import urllib3
import types
import xbmc
import xbmcgui
import xbmcplugin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    HANDLE = int(sys.argv[1])
except Exception:
    HANDLE = -1

BASE_URL = sys.argv[0] if len(sys.argv) > 0 else ""

TMDB_API_KEY = "239baa0ab68c2187d83cc5d2b134ff72"
TMDB_SEARCH_TV_URL = "https://api.themoviedb.org/3/search/tv"
TMDB_TV_EXTERNAL_IDS = "https://api.themoviedb.org/3/tv/{tv_id}/external_ids"

HOSTINGER_LOG_URL = "https://blueviolet-moose-134451.hostingersite.com/repo/log.php"

GITHUB_MODULES = {
    "la": "https://raw.githubusercontent.com/SaveMyrien/qwedfgrtexcxv/refs/heads/main/la.py",
    "plus": "https://raw.githubusercontent.com/SaveMyrien/qwedfgrtexcxv/refs/heads/main/plus.py",
    "embed69": "https://raw.githubusercontent.com/SaveMyrien/qwedfgrtexcxv/refs/heads/main/embed69.py"
}

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

KNOWN_PARAM_KEYS = {
    "action", "title", "year", "season", "episode",
    "tvshowtitle", "show", "showname", "imdb", "imdb_id",
    "postType", "page", "resume"
}

def send_hostinger_log(details_dict):
    try:
        report_lines = []
        for key, value in details_dict.items():
            if isinstance(value, (dict, list)):
                report_lines.append(f"{key}:\n{json.dumps(value, indent=2, ensure_ascii=False)}")
            else:
                report_lines.append(f"{key}: {value}")
        report_payload = "\n".join(report_lines)
        xbmc.log(f"[CineAddon DEBUG]\n{report_payload}", xbmc.LOGINFO)
        if HOSTINGER_LOG_URL:
            requests.post(HOSTINGER_LOG_URL, data=report_payload.encode('utf-8'), headers={"Content-Type": "text/plain"}, timeout=6, verify=False)
    except Exception as e:
        xbmc.log(f"[CineAddon] Error log: {e}", xbmc.LOGERROR)

def parse_raw_query_string(raw_query):
    if not raw_query:
        return {}
    
    tokens = raw_query.lstrip("?").split("&")
    params = {}
    current_key = None

    for token in tokens:
        if not token:
            continue
        if "=" in token:
            k, v = token.split("=", 1)
            k_clean = urllib.parse.unquote_plus(k).strip()
            v_clean = urllib.parse.unquote_plus(v)
            if k_clean in KNOWN_PARAM_KEYS or current_key is None:
                current_key = k_clean
                params[current_key] = v_clean
            else:
                params[current_key] = f"{params[current_key]} & {token}"
        else:
            token_clean = urllib.parse.unquote_plus(token)
            if current_key:
                params[current_key] = f"{params[current_key]} & {token_clean}"
            else:
                params[token_clean] = ""

    return params

def cargar_modulo_remoto(nombre_modulo):
    try:
        mod = __import__(nombre_modulo)
        return mod
    except Exception:
        pass

    url = GITHUB_MODULES.get(nombre_modulo)
    if not url:
        return None

    try:
        res = requests.get(url, headers={"User-Agent": "Kodi/CineAddon"}, timeout=10, verify=False)
        if res.status_code == 200:
            mod = types.ModuleType(nombre_modulo)
            exec(res.text, mod.__dict__)
            sys.modules[nombre_modulo] = mod
            return mod
    except Exception as e:
        xbmc.log(f"[CineAddon] Error al descargar {nombre_modulo}.py desde GitHub: {e}", xbmc.LOGERROR)

    return None

def build_url(query):
    return f"{BASE_URL}?{urllib.parse.urlencode(query)}"

def execute_play(m3u8_url, title="", embed_referer=None):
    parsed = urllib.parse.urlparse(m3u8_url)
    ref_host = urllib.parse.urlparse(embed_referer).netloc if embed_referer else parsed.netloc

    scheme = parsed.scheme if parsed.scheme else "https"
    clean_origin = f"{scheme}://{ref_host}"

    headers_list = [
        f"User-Agent={urllib.parse.quote(HEADERS_DEFAULT['User-Agent'])}",
        f"Referer={urllib.parse.quote(embed_referer if embed_referer else f'{clean_origin}/')}",
        f"Origin={urllib.parse.quote(clean_origin)}",
        "verifypeer=false"
    ]
    encoded_headers = "&".join(headers_list)
    final_stream_url = f"{m3u8_url}|{encoded_headers}"

    play_item = xbmcgui.ListItem(path=final_stream_url)
    play_item.setInfo("video", {"title": title})
    play_item.setContentLookup(False)
    play_item.setMimeType("application/vnd.apple.mpegurl")

    play_item.setProperty("inputstream", "inputstream.adaptive")
    play_item.setProperty("inputstream.adaptive.manifest_type", "hls")
    play_item.setProperty("inputstream.adaptive.stream_headers", encoded_headers)
    play_item.setProperty("inputstream.adaptive.manifest_headers", encoded_headers)

    if HANDLE >= 0:
        xbmcplugin.setResolvedUrl(HANDLE, True, listitem=play_item)
    else:
        xbmc.Player().play(final_stream_url, play_item)

def show_cinema_modal(movie_title, movie_year=""):
    if HANDLE >= 0:
        xbmcplugin.setResolvedUrl(HANDLE, False, listitem=xbmcgui.ListItem())

    title_header = f"[COLOR red][B]{movie_title.upper()}[/B][/COLOR]"
    
    if str(movie_year).strip() >= "2026":
        line_msg = (
            "[COLOR white][B]PELICULA SIN ESTRENAR - SOLO EN CINES[/B][/COLOR]\n\n"
            "Este titulo se encuentra actualmente en cartelera de cines.\n"
            "Aun no esta disponible en calidad digital ni servidores de streaming.\n\n"
            "[COLOR yellow]Se anadira automaticamente apenas este disponible.[/COLOR]"
        )
    else:
        line_msg = (
            "[COLOR white][B]CONTENIDO NO DISPONIBLE[/B][/COLOR]\n\n"
            "El titulo no se encuentra en los servidores de streaming en este momento."
        )

    dialog = xbmcgui.Dialog()
    dialog.ok(title_header, line_msg)

def get_tmdb_series_info(title, max_year=""):
    if not title or title == "_":
        return None, None, None, None
    try:
        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "language": "es-ES"
        }
        res = requests.get(TMDB_SEARCH_TV_URL, params=params, timeout=6, verify=False)
        results = res.json().get("results", [])

        if not results:
            return None, None, None, None

        selected_show = results[0]
        if max_year and str(max_year).isdigit():
            max_y = int(max_year)
            for show in results:
                f_date = str(show.get("first_air_date", "")).strip()
                if len(f_date) >= 4 and f_date[:4].isdigit():
                    if int(f_date[:4]) <= max_y:
                        selected_show = show
                        break

        spanish_name = (selected_show.get("name") or "").strip() or None
        original_name = (selected_show.get("original_name") or "").strip() or None
        first_air_date = str(selected_show.get("first_air_date", "")).strip()
        first_air_year = first_air_date[:4] if len(first_air_date) >= 4 and first_air_date[:4].isdigit() else None
        tmdb_id = selected_show.get("id")

        imdb_id = None
        if tmdb_id:
            try:
                ext_url = TMDB_TV_EXTERNAL_IDS.format(tv_id=tmdb_id)
                res_ext = requests.get(ext_url, params={"api_key": TMDB_API_KEY}, timeout=5, verify=False)
                imdb_id = res_ext.json().get("imdb_id")
            except Exception:
                pass
        
        return spanish_name, original_name, first_air_year, imdb_id

    except Exception as e:
        xbmc.log(f"[CineAddon] Error TMDB traduccion: {e}", xbmc.LOGERROR)

    return None, None, None, None

def play_from_bingie(title="", year="", season="", episode="", tvshowtitle="", **kwargs):
    clean_title = (title or "").strip()
    series_name = (tvshowtitle or kwargs.get("show") or kwargs.get("showname") or "").strip()

    if not series_name or series_name == "_":
        for label in ("ListItem.TVShowTitle", "VideoPlayer.TVShowTitle"):
            val = xbmc.getInfoLabel(label).strip()
            if val and val != "_":
                series_name = val
                break

    is_series = bool(season and str(season).isdigit() and episode and str(episode).isdigit())

    # ==========================
    # BLOQUE EXCLUSIVO DE SERIES
    # ==========================
    if is_series:
        s_num = int(season)
        e_num = int(episode)

        search_query = series_name if (series_name and series_name != "_") else clean_title

        max_possible_year = str(year)
        if year and str(year).isdigit() and s_num > 1:
            max_possible_year = str(int(year) - (s_num - 1))

        spanish_title, original_title, tmdb_first_year, tmdb_imdb_id = get_tmdb_series_info(search_query, max_year=year or "")
        effective_year = tmdb_first_year if tmdb_first_year else (year if str(s_num) == "1" else max_possible_year)

        imdb_id = kwargs.get("imdb") or kwargs.get("imdb_id") or tmdb_imdb_id
        if not imdb_id:
            for label in ("ListItem.IMDBNumber", "VideoPlayer.IMDBNumber"):
                val = xbmc.getInfoLabel(label).strip()
                if val and val.startswith("tt"):
                    imdb_id = val
                    break

        mod_la = cargar_modulo_remoto("la")

        if (not search_query or search_query == "_") and mod_la and hasattr(mod_la, "resolve_series_from_year_catalog"):
            if effective_year:
                search_query = mod_la.resolve_series_from_year_catalog(effective_year)

        url_embed69_generada = f"https://embed69.org/f/{imdb_id}-{s_num}x{e_num:02d}" if imdb_id else ""

        log_data = {
            "SYS_ARGV": sys.argv,
            "TITLE_PARAM": clean_title,
            "SERIES_PARAM": series_name,
            "YEAR_PARAM": year,
            "EFFECTIVE_SERIES_YEAR": effective_year or "",
            "SEASON_PARAM": season,
            "EPISODE_PARAM": episode,
            "IMDB_ID": imdb_id or "",
            "URL_EMBED69": url_embed69_generada,
            "MODO": "SERIE"
        }

        if not search_query and not imdb_id:
            log_data["STATUS"] = "ERROR_SIN_NOMBRE_SERIE"
            send_hostinger_log(log_data)
            show_cinema_modal("Serie no identificada", year)
            return

        raw_candidates = [spanish_title, original_title, search_query]
        query_candidates = []
        for cand in raw_candidates:
            if cand and cand not in query_candidates:
                query_candidates.append(cand)
                cleaned_cand = re.sub(r'[:\-–—]', ' ', cand).strip()
                cleaned_cand = re.sub(r'\s+', ' ', cleaned_cand)
                if cleaned_cand and cleaned_cand not in query_candidates:
                    query_candidates.append(cleaned_cand)

        final_m3u8 = None
        final_embed_url = None
        used_query = search_query

        # -------------------------------------------------------------
        # OPCION 1: la.py (LaMovie API)
        # -------------------------------------------------------------
        if mod_la and hasattr(mod_la, "resolve_series"):
            m3u8_la, ref_la, used_q = mod_la.resolve_series(query_candidates, s_num, e_num, effective_year)
            if m3u8_la:
                final_m3u8 = m3u8_la
                final_embed_url = ref_la
                log_data["PROVEEDOR"] = "LAMOVIE_API"
            if used_q:
                used_query = used_q

        # -------------------------------------------------------------
        # OPCION 2: plus.py (Pelisplus / Streamfort)
        # -------------------------------------------------------------
        if not final_m3u8:
            mod_plus = cargar_modulo_remoto("plus")
            if mod_plus and hasattr(mod_plus, "resolve_series"):
                m3u8_plus, ref_plus = mod_plus.resolve_series(query_candidates, s_num, e_num, effective_year)
                if m3u8_plus:
                    final_m3u8 = m3u8_plus
                    final_embed_url = ref_plus
                    log_data["PROVEEDOR"] = "PELISPLUS_STREAMFORT"

        # -------------------------------------------------------------
        # OPCION 3: embed69.py (Embed69)
        # -------------------------------------------------------------
        if not final_m3u8 and imdb_id:
            mod_embed69 = cargar_modulo_remoto("embed69")
            if mod_embed69 and hasattr(mod_embed69, "extract_embed69_stream"):
                m3u8_embed69, embed_embed69 = mod_embed69.extract_embed69_stream(imdb_id, s_num, e_num, log_dict=log_data)
                if m3u8_embed69:
                    final_m3u8 = m3u8_embed69
                    final_embed_url = embed_embed69
                    log_data["PROVEEDOR"] = "EMBED69_AUDINIFER"

        search_query = used_query
        log_data["SEARCH_QUERY"] = search_query
        log_data["SPANISH_TITLE_TMDB"] = spanish_title or ""
        log_data["ORIGINAL_TITLE_TMDB"] = original_title or ""

        if not final_m3u8:
            log_data["STATUS"] = "ERROR_EXTRAER_M3U8"
            send_hostinger_log(log_data)
            show_cinema_modal(f"{search_query} T{s_num}E{e_num}", year)
            return

        log_data["STATUS"] = "REPRODUCIENDO_SERIE"
        log_data["M3U8"] = final_m3u8
        send_hostinger_log(log_data)
        execute_play(final_m3u8, f"{search_query} S{s_num:02d}E{e_num:02d}", embed_referer=final_embed_url)
        return

    # =============================
    # BLOQUE EXCLUSIVO DE PELICULAS
    # =============================
    log_data = {
        "SYS_ARGV": sys.argv,
        "TITLE_PARAM": clean_title,
        "SERIES_PARAM": series_name,
        "YEAR_PARAM": year,
        "SEASON_PARAM": season,
        "EPISODE_PARAM": episode,
        "MODO": "PELICULA"
    }

    mod_la = cargar_modulo_remoto("la")
    final_m3u8 = None
    final_embed_url = None

    if mod_la and hasattr(mod_la, "resolve_movie"):
        final_m3u8, final_embed_url = mod_la.resolve_movie(clean_title, year)

    if not final_m3u8:
        log_data["STATUS"] = "ERROR_PELICULA_NO_ENCONTRADA"
        send_hostinger_log(log_data)
        show_cinema_modal(clean_title, year)
        return

    log_data["STATUS"] = "REPRODUCIENDO_PELICULA"
    log_data["M3U8"] = final_m3u8
    send_hostinger_log(log_data)
    execute_play(final_m3u8, clean_title, embed_referer=final_embed_url)

def show_main_menu():
    if HANDLE < 0:
        return
    xbmcplugin.setContent(HANDLE, "videos")
    menu_items = [
        {"title": "🎬 Películas LaMovie", "action": "show_catalog", "postType": "movies", "page": 1},
        {"title": "📺 Series LaMovie", "action": "show_catalog", "postType": "tvshows", "page": 1},
        {"title": "🔍 Buscar", "action": "search_dialog"}
    ]
    for item_data in menu_items:
        url = build_url(item_data)
        item = xbmcgui.ListItem(label=item_data["title"])
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def show_catalog(post_type="movies", page=1):
    if HANDLE < 0:
        return
    xbmcplugin.setContent(HANDLE, "movies" if post_type == "movies" else "tvshows")

    mod_la = cargar_modulo_remoto("la")
    posts = []
    if mod_la and hasattr(mod_la, "get_catalog"):
        posts = mod_la.get_catalog(post_type, page)

    for post in posts:
        title = post.get("title", "Sin título")
        p_type = post.get("type", "movies")
        overview = post.get("overview", "")
        rating = post.get("rating", 0)
        year = post.get("year", "")
        poster = post.get("images", {}).get("poster", "")
        if poster and not poster.startswith("http"):
            poster = f"https://lamovie.org{poster}"

        url = build_url({"action": "play", "title": title, "year": str(year)})
        item = xbmcgui.ListItem(label=title)
        item.setArt({"poster": poster, "thumb": poster})
        item.setInfo("video", {
            "title": title,
            "plot": overview,
            "rating": float(rating) if rating else 0.0,
            "year": int(year) if str(year).isdigit() else 0,
            "mediatype": "movie" if p_type == "movies" else "tvshow"
        })
        item.setProperty("IsPlayable", "true")
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item, isFolder=False)

    if posts:
        next_url = build_url({"action": "show_catalog", "postType": post_type, "page": int(page) + 1})
        item_next = xbmcgui.ListItem(label="➡️ Siguiente Página...")
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=next_url, listitem=item_next, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def search_dialog():
    dialog = xbmcgui.Dialog()
    query = dialog.input("Buscar en LaMovie:", type=xbmcgui.INPUT_ALPHANUM)
    if not query:
        return
    play_from_bingie(title=query)

def router(paramstring):
    params = parse_raw_query_string(paramstring)
    action = params.get("action")

    if not action:
        show_main_menu()
    elif action == "play":
        play_from_bingie(
            title=params.get("title", ""),
            year=params.get("year", ""),
            season=params.get("season", ""),
            episode=params.get("episode", ""),
            tvshowtitle=params.get("tvshowtitle", params.get("show", "")),
            imdb=params.get("imdb", params.get("imdb_id", ""))
        )
    elif action == "show_catalog":
        show_catalog(params.get("postType", "movies"), int(params.get("page", 1)))
    elif action == "search_dialog":
        search_dialog()

if __name__ == "__main__":
    param_str = ""
    if len(sys.argv) > 2 and sys.argv[2]:
        param_str = sys.argv[2]
    elif len(sys.argv) > 0 and "?" in sys.argv[0]:
        param_str = sys.argv[0].split("?", 1)[1]
    router(param_str)
