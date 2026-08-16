# -*- coding: utf-8 -*-
import sys
import re
import urllib.parse
import json
import uuid
import time
import base64
import hashlib
import requests
import urllib3
import xbmc
import xbmcgui
import xbmcplugin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    HANDLE = int(sys.argv[1])
except Exception:
    HANDLE = -1

BASE_URL = sys.argv[0] if len(sys.argv) > 0 else ""

API_BASE_URL = "https://lamovie.org"
API_SEARCH = f"{API_BASE_URL}/wp-api/v1/search"
API_EPISODES = f"{API_BASE_URL}/wp-api/v1/single/episodes/list"
API_PLAYER = f"{API_BASE_URL}/wp-api/v1/player"

TMDB_API_KEY = "239baa0ab68c2187d83cc5d2b134ff72"
TMDB_SEARCH_TV_URL = "https://api.themoviedb.org/3/search/tv"
TMDB_TV_EXTERNAL_IDS = "https://api.themoviedb.org/3/tv/{tv_id}/external_ids"

HOSTINGER_LOG_URL = "https://blueviolet-moose-134451.hostingersite.com/repo/log.php"

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://lamovie.org/",
    "Origin": "https://lamovie.org",
    "Cache-Control": "no-cache"
}

HEADERS_PELISPLUS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://pelisplustv.net/"
}

# =========================================================================
# MOTOR AES-128 / AES-256 CBC EN PYTHON PURO
# =========================================================================
SBOX = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
]

INV_SBOX = [0] * 256
for i, val in enumerate(SBOX):
    INV_SBOX[val] = i

RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]

def _xtime(a):
    return ((a << 1) ^ 0x1B) & 0xFF if (a & 0x80) else (a << 1)

def _mul(a, b):
    res = 0
    while b:
        if b & 1:
            res ^= a
        a = _xtime(a)
        b >>= 1
    return res

class PureAES:
    def __init__(self, key):
        self.key = list(key)
        self.nk = len(self.key) // 4
        self.nr = self.nk + 6
        self._key_expansion()

    def _key_expansion(self):
        w = [self.key[4*i : 4*(i+1)] for i in range(self.nk)]
        for i in range(self.nk, 4 * (self.nr + 1)):
            temp = list(w[i - 1])
            if i % self.nk == 0:
                temp = [SBOX[temp[1]], SBOX[temp[2]], SBOX[temp[3]], SBOX[temp[0]]]
                temp[0] ^= RCON[i // self.nk]
            elif self.nk > 6 and (i % self.nk) == 4:
                temp = [SBOX[x] for x in temp]
            w.append([w[i - self.nk][j] ^ temp[j] for j in range(4)])
        self.round_keys = w

    def _inv_sub_bytes(self, state):
        for r in range(4):
            for c in range(4):
                state[r][c] = INV_SBOX[state[r][c]]

    def _inv_shift_rows(self, state):
        state[1] = [state[1][3], state[1][0], state[1][1], state[1][2]]
        state[2] = [state[2][2], state[2][3], state[2][0], state[2][1]]
        state[3] = [state[3][1], state[3][2], state[3][3], state[3][0]]

    def _inv_mix_columns(self, state):
        for c in range(4):
            s0 = state[0][c]
            s1 = state[1][c]
            s2 = state[2][c]
            s3 = state[3][c]
            state[0][c] = _mul(0x0e, s0) ^ _mul(0x0b, s1) ^ _mul(0x0d, s2) ^ _mul(0x09, s3)
            state[1][c] = _mul(0x09, s0) ^ _mul(0x0e, s1) ^ _mul(0x0b, s2) ^ _mul(0x0d, s3)
            state[2][c] = _mul(0x0d, s0) ^ _mul(0x09, s1) ^ _mul(0x0e, s2) ^ _mul(0x0b, s3)
            state[3][c] = _mul(0x0b, s0) ^ _mul(0x0d, s1) ^ _mul(0x09, s2) ^ _mul(0x0e, s3)

    def _add_round_key(self, state, round_num):
        for c in range(4):
            k = self.round_keys[round_num * 4 + c]
            for r in range(4):
                state[r][c] ^= k[r]

    def decrypt_block(self, block):
        state = [[block[r + 4 * c] for c in range(4)] for r in range(4)]
        self._add_round_key(state, self.nr)
        for rnd in range(self.nr - 1, 0, -1):
            self._inv_shift_rows(state)
            self._inv_sub_bytes(state)
            self._add_round_key(state, rnd)
            self._inv_mix_columns(state)
        self._inv_shift_rows(state)
        self._inv_sub_bytes(state)
        self._add_round_key(state, 0)
        return bytes([state[r][c] for c in range(4) for r in range(4)])

def descifrar_aes_cbc(encrypted_b64, aes_key):
    try:
        raw_bytes = base64.b64decode(encrypted_b64)
        iv = raw_bytes[:16]
        ciphertext = raw_bytes[16:]

        cipher = PureAES(aes_key)
        decrypted = bytearray()
        prev = iv
        for i in range(0, len(ciphertext), 16):
            block = ciphertext[i:i+16]
            dec_block = cipher.decrypt_block(block)
            decrypted.extend(b ^ p for b, p in zip(dec_block, prev))
            prev = block

        pad_len = decrypted[-1]
        if 1 <= pad_len <= 16:
            texto = decrypted[:-pad_len].decode('utf-8', errors='ignore')
        else:
            texto = decrypted.decode('utf-8', errors='ignore')
        return texto
    except Exception:
        return None

def resolver_pow_embed69(challenge, difficulty, salt):
    prefix = '0' * int(difficulty)
    nonce = 0
    while True:
        data_to_hash = f"{challenge}{nonce}".encode('utf-8')
        h = hashlib.sha256(data_to_hash).hexdigest()
        if h.startswith(prefix):
            key_data = f"{challenge}{nonce}{salt}".encode('utf-8')
            aes_key = hashlib.sha256(key_data).digest()
            return nonce, aes_key
        nonce += 1

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
        xbmc.log(f"[CineAddon] Error unpacker: {err}", xbmc.LOGERROR)
        return ""

def sanitize_m3u8_url(url):
    if not url:
        return None
    clean = url.strip()
    clean = re.sub(r'["\'\\].*$', '', clean)
    clean = clean.replace('&amp;', '&')
    return clean

# =========================================================================
# COMPROBADOR DE ENLACES M3U8 (VALIDA RESPUESTA 200 OK + #EXTM3U)
# =========================================================================
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

def obtener_mejor_calidad_streamwish(master_url):
    try:
        match = re.search(r'(https?://[^/]+/hls2/\d+/\d+/[^/]+?\.urlset/)master\.m3u8(\?.*)?', master_url)
        if not match:
            return master_url

        base_urlset = match.group(1)
        query_params = match.group(2) or ""

        headers_check = {
            "User-Agent": HEADERS_DEFAULT["User-Agent"],
            "Referer": "https://audinifer.com/",
            "Origin": "https://audinifer.com"
        }

        variantes = ["index-f3-v1-a1.m3u8", "index-f2-v1-a1.m3u8", "index-f1-v1-a1.m3u8"]

        for var_m3u8 in variantes:
            target_url = f"{base_urlset}{var_m3u8}{query_params}"
            try:
                res = requests.get(target_url, headers=headers_check, timeout=3, verify=False)
                if res.status_code == 200 and "#EXTM3U" in res.text:
                    return target_url
            except Exception:
                pass

    except Exception:
        pass

    return master_url

# =========================================================================
# EXTRACTOR EMBED69 / STREAMWISH / AUDINIFER
# =========================================================================
def extract_embed69_m3u8_from_imdb(imdb_id, s_num, e_num, log_dict=None):
    if not imdb_id:
        return None, None
    try:
        ep_tag = f"{imdb_id}-{int(s_num)}x{int(e_num):02d}"
        embed_url = f"https://embed69.org/f/{ep_tag}"

        if log_dict is not None:
            log_dict["EMBED69_URL_PROCESADA"] = embed_url

        headers = {
            "User-Agent": HEADERS_DEFAULT["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": "https://sololatino.net/",
            "Origin": "https://sololatino.net"
        }

        res = requests.get(embed_url, headers=headers, timeout=15, verify=False)
        if res.status_code != 200:
            if log_dict is not None:
                log_dict["EMBED69_ERROR"] = f"HTTP_{res.status_code}"
            return None, None
        
        html_str = res.text

        m_challenge = re.search(r"POW_CHALLENGE\s*=\s*['\"]([^'\"]+)['\"]", html_str)
        m_difficulty = re.search(r"POW_DIFFICULTY\s*=\s*(\d+)", html_str)
        m_salt = re.search(r"POW_SALT\s*=\s*['\"]([^'\"]+)['\"]", html_str)
        m_datalink = re.search(r"let\s+dataLink\s*=\s*(\[\{.*?\}\]);", html_str, re.DOTALL)

        if not (m_challenge and m_difficulty and m_salt and m_datalink):
            if log_dict is not None:
                log_dict["EMBED69_ERROR"] = "PARAMS_POW_NO_ENCONTRADOS"
            return None, None

        challenge = m_challenge.group(1)
        difficulty = int(m_difficulty.group(1))
        salt = m_salt.group(1)
        data_link = json.loads(m_datalink.group(1))

        _, aes_key = resolver_pow_embed69(challenge, difficulty, salt)

        candidatos_embeds = []
        for item in data_link:
            for embed in item.get("sortedEmbeds", []):
                srv_name = embed.get("servername", "").lower()
                link_enc = embed.get("link", "")
                real_link = descifrar_aes_cbc(link_enc, aes_key)
                if real_link and real_link.startswith("http"):
                    candidatos_embeds.append((srv_name, real_link))

            for dl in item.get("downloadEmbeds", []):
                srv_name = dl.get("servername", "").lower()
                link_enc = dl.get("link", "")
                real_link = descifrar_aes_cbc(link_enc, aes_key)
                if real_link and real_link.startswith("http"):
                    candidatos_embeds.append((srv_name, real_link))

        if not candidatos_embeds:
            if log_dict is not None:
                log_dict["EMBED69_ERROR"] = "DATALINK_SIN_ENLACES_VALIDOS"
            return None, None

        if log_dict is not None:
            log_dict["EMBED69_SERVERS_DISPONIBLES"] = [f"{n}: {u}" for n, u in candidatos_embeds]

        url_target_embed = None
        for srv_name, real_url in candidatos_embeds:
            if any(k in srv_name or k in real_url for k in ["streamwish", "hglink", "audinifer", "ghbrisk"]):
                url_target_embed = real_url
                break
        
        if not url_target_embed:
            url_target_embed = candidatos_embeds[0][1]

        if any(h in url_target_embed for h in ["hglink.to", "streamwish", "ghbrisk.com", "audinifer"]):
            match_code = re.search(r'/(?:e|d)/([a-zA-Z0-9]+)', url_target_embed)
            if match_code:
                file_code = match_code.group(1)
                url_player_final = f"https://audinifer.com/e/{file_code}"
            else:
                url_player_final = re.sub(r'https?://[^/]+', 'https://audinifer.com', url_target_embed)
        else:
            url_player_final = url_target_embed

        if log_dict is not None:
            log_dict["URL_REPRODUCTOR_OBJETIVO"] = url_player_final

        headers_audi = {
            "User-Agent": HEADERS_DEFAULT["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": embed_url
        }

        res_audi = requests.get(url_player_final, headers=headers_audi, timeout=15, verify=False)
        if res_audi.status_code != 200:
            if log_dict is not None:
                log_dict["REPRODUCTOR_ERROR"] = f"HTTP_{res_audi.status_code}"
            return None, None

        unpacked_js = unpack_dean_edwards_js_exact(res_audi.text)
        search_target = unpacked_js if unpacked_js else res_audi.text

        m3u8_matches = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', search_target)
        if not m3u8_matches:
            m3u8_matches = re.findall(r'file\s*:\s*["\'](https?://[^"\']+)["\']', search_target)

        if m3u8_matches:
            clean_master = sanitize_m3u8_url(m3u8_matches[0].replace("\\/", "/"))
            mejor_m3u8 = obtener_mejor_calidad_streamwish(clean_master)
            if verificar_stream_online(mejor_m3u8, "https://audinifer.com/"):
                return mejor_m3u8, "https://audinifer.com/"
            elif verificar_stream_online(clean_master, "https://audinifer.com/"):
                return clean_master, "https://audinifer.com/"
        else:
            if log_dict is not None:
                log_dict["REPRODUCTOR_ERROR"] = "M3U8_NO_ENCONTRADO_EN_JS"

    except Exception as e:
        if log_dict is not None:
            log_dict["EMBED69_EXCEPTION"] = str(e)
        xbmc.log(f"[CineAddon] Error extraccion Embed69: {e}", xbmc.LOGERROR)

    return None, None

def send_hostinger_log(details_dict):
    try:
        report_lines = []
        for key, value in details_dict.items():
            if isinstance(value, (dict, list)):
                report_lines.append(f"{key}:\n{json.dumps(value, indent=2, ensure_ascii=False)}")
            else:
                report_lines.append(f"{key}: {value}")
        report_payload = "\n".join(report_lines)
        xbmc.log(f"[LaMovie DEBUG]\n{report_payload}", xbmc.LOGINFO)
        requests.post(HOSTINGER_LOG_URL, data=report_payload.encode('utf-8'), headers={"Content-Type": "text/plain"}, timeout=6, verify=False)
    except Exception as e:
        xbmc.log(f"[CineAddon] Error log: {e}", xbmc.LOGERROR)

# =========================================================================
# EXTRACTOR VIMEOS / LAMOVIE API (CON VALIDACIÓN DE VIDA REAL 200 OK)
# =========================================================================
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

        html = res_embed.text

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

        unpacked_js = unpack_dean_edwards_js_exact(html)
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
            html_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html, re.I) or \
                         re.search(r'(https?://[^\s"\'<>\\]+?\.m3u8\?[^\s"\'<>\\]+)', html, re.I)
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

            headers_stream = dict(HEADERS_DEFAULT)
            headers_stream["Referer"] = target_url
            headers_stream["Origin"] = "https://vimeos.net"

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
        xbmc.log(f"[CineAddon] Error extraccion vimeos: {err}", xbmc.LOGERROR)

    return None, None

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
        xbmc.log(f"[CineAddon] Error busqueda Pelisplus: {e}", xbmc.LOGERROR)

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
        xbmc.log(f"[CineAddon] Error extraccion Streamfort: {e}", xbmc.LOGERROR)

    return None, None

def build_url(query):
    return f"{BASE_URL}?{urllib.parse.urlencode(query)}"

# =========================================================================
# REPRODUCTOR KODI (CABECERAS ADAPTATIVAS CON ORIGIN DINÁMICO)
# =========================================================================
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

def normalize_string(text):
    if not text:
        return ""
    text = re.sub(r'\(\d{4}\)', '', text)
    replacements = (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("Á", "a"), ("É", "e"), ("Í", "i"), ("Ó", "o"), ("Ú", "u"),
        ("ñ", "n"), ("Ñ", "n")
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

    if target_year:
        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            if clean_target_tokens == p_clean.replace(" ", "") and p_year == target_year:
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

    return None

def find_best_series_match(posts, search_title, target_year=""):
    if not posts:
        return None
    
    clean_target = normalize_string(search_title)
    clean_target_tokens = clean_target.replace(" ", "")
    target_year = str(target_year).strip()

    if target_year:
        for post in posts:
            p_clean = normalize_string(post.get("title", ""))
            p_year = extract_year_from_post(post)
            if clean_target_tokens == p_clean.replace(" ", "") and p_year == target_year:
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
            xbmc.log(f"[CineAddon] Error lista episodios: {e}", xbmc.LOGERROR)
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

        if not search_query or search_query == "_":
            if effective_year:
                search_query = resolve_series_from_year_catalog(effective_year)

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

        series_post = None
        used_query = search_query

        # -------------------------------------------------------------
        # OPCIÓN 1: LaMovie API (Con comprobación de stream activo)
        # -------------------------------------------------------------
        for candidate_query in query_candidates:
            search_url = f"{API_SEARCH}?filter=%7B%7D&postType=any&q={urllib.parse.quote(candidate_query)}&postsPerPage=26"
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

        search_query = used_query
        log_data["SEARCH_QUERY"] = search_query
        log_data["SPANISH_TITLE_TMDB"] = spanish_title or ""
        log_data["ORIGINAL_TITLE_TMDB"] = original_title or ""

        final_m3u8 = None
        final_embed_url = None

        if series_post:
            series_id = series_post.get("_id")
            episode_id = get_episode_post_id(series_id, s_num, e_num)

            if episode_id:
                player_url = f"{API_PLAYER}?postId={episode_id}&demo=0"
                try:
                    res_player = requests.get(player_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
                    embeds = res_player.json().get("data", {}).get("embeds", [])
                except Exception:
                    embeds = []

                if embeds:
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
                        m3u8_cand, ref_cand = extract_vimeos_cdn_stream(candidate_embed.get("url", ""))
                        if m3u8_cand:
                            final_m3u8 = m3u8_cand
                            final_embed_url = ref_cand
                            log_data["PROVEEDOR"] = "LAMOVIE_API"
                            break

        # -------------------------------------------------------------
        # OPCIÓN 2: Pelisplustv / Streamfort (Con comprobación activa)
        # -------------------------------------------------------------
        if not final_m3u8:
            for candidate_query in query_candidates:
                pelisplus_url = search_pelisplus_series_url(candidate_query, effective_year)
                if pelisplus_url:
                    m3u8_backup, embed_backup = extract_streamfort_m3u8_from_pelisplus(pelisplus_url, s_num, e_num)
                    if m3u8_backup:
                        final_m3u8 = m3u8_backup
                        final_embed_url = embed_backup
                        log_data["PROVEEDOR"] = "PELISPLUS_STREAMFORT"
                        break

        # -------------------------------------------------------------
        # OPCIÓN 3: Embed69 / Audinifer (Streamwish por IMDb ID)
        # -------------------------------------------------------------
        if not final_m3u8 and imdb_id:
            m3u8_embed69, embed_embed69 = extract_embed69_m3u8_from_imdb(imdb_id, s_num, e_num, log_dict=log_data)
            if m3u8_embed69:
                final_m3u8 = m3u8_embed69
                final_embed_url = embed_embed69
                log_data["PROVEEDOR"] = "EMBED69_AUDINIFER"

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
    # BLOQUE ORIGINAL DE PELÍCULAS
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

    search_url = f"{API_SEARCH}?filter=%7B%7D&postType=any&q={urllib.parse.quote(clean_title)}&postsPerPage=15"
    
    try:
        res = requests.get(search_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
        posts = res.json().get("data", {}).get("posts", [])
    except Exception as e:
        xbmc.log(f"[CineAddon] Error búsqueda API: {e}", xbmc.LOGERROR)
        posts = []

    if not posts:
        sanitized_query = re.sub(r'[&:/\-]', ' ', clean_title).split()[0]
        search_url_alt = f"{API_SEARCH}?filter=%7B%7D&postType=any&q={urllib.parse.quote(sanitized_query)}&postsPerPage=15"
        try:
            res_alt = requests.get(search_url_alt, headers=HEADERS_DEFAULT, timeout=10, verify=False)
            posts = res_alt.json().get("data", {}).get("posts", [])
        except Exception:
            posts = []

    selected_post = find_best_post_match(posts, clean_title, year)

    if not selected_post:
        log_data["STATUS"] = "ERROR_PELICULA_NO_ENCONTRADA"
        send_hostinger_log(log_data)
        show_cinema_modal(clean_title, year)
        return

    post_id = selected_post.get("_id")

    player_url = f"{API_PLAYER}?postId={post_id}&demo=0"
    try:
        res_player = requests.get(player_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
        embeds = res_player.json().get("data", {}).get("embeds", [])
    except Exception as e:
        xbmc.log(f"[CineAddon] Error API Player: {e}", xbmc.LOGERROR)
        embeds = []

    if not embeds:
        log_data["STATUS"] = "ERROR_SIN_EMBEDS"
        send_hostinger_log(log_data)
        show_cinema_modal(clean_title, year)
        return

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

    final_m3u8 = None
    final_embed_url = None
    for candidate_embed in ordered_embeds:
        final_m3u8, final_embed_url = extract_vimeos_cdn_stream(candidate_embed.get("url", ""))
        if final_m3u8:
            break

    if not final_m3u8:
        log_data["STATUS"] = "ERROR_EXTRAER_M3U8"
        send_hostinger_log(log_data)
        show_cinema_modal(clean_title, year)
        return

    log_data["STATUS"] = "REPRODUCIENDO_PELICULA"
    log_data["M3U8"] = final_m3u8
    send_hostinger_log(log_data)
    execute_play(final_m3u8, title, embed_referer=final_embed_url)

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
    req_url = f"{API_SEARCH}?filter=%7B%7D&postType={post_type}&page={page}&postsPerPage=24"
    try:
        res = requests.get(req_url, headers=HEADERS_DEFAULT, timeout=10, verify=False)
        posts = res.json().get("data", {}).get("posts", [])
    except Exception as e:
        xbmc.log(f"[CineAddon] Error catálogo: {e}", xbmc.LOGERROR)
        posts = []

    for post in posts:
        title = post.get("title", "Sin título")
        p_type = post.get("type", "movies")
        overview = post.get("overview", "")
        rating = post.get("rating", 0)
        year = post.get("year", "")
        poster = post.get("images", {}).get("poster", "")
        if poster and not poster.startswith("http"):
            poster = f"{API_BASE_URL}{poster}"

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
    params = dict(urllib.parse.parse_qsl(paramstring))
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
        param_str = sys.argv[2][1:]
    elif len(sys.argv) > 0 and "?" in sys.argv[0]:
        param_str = sys.argv[0].split("?", 1)[1]
    router(param_str)