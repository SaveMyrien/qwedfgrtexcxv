# -*- coding: utf-8 -*-
import re
import json
import base64
import hashlib
import requests
import urllib.parse
import urllib3

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
    HAVE_CRYPTOGRAPHY = True
except Exception:
    HAVE_CRYPTOGRAPHY = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://sololatino.net/",
    "Origin": "https://sololatino.net"
}

class PureAES:
    def __init__(self, key):
        self.key = key
        self._key_expansion()

    def _key_expansion(self):
        sbox = [
            0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
            0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
            0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
            0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
            0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
            0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
            0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
            0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
            0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
            0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
            0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5e,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
            0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
            0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
            0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
            0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
            0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
        ]
        self.inv_sbox = [0] * 256
        for i, val in enumerate(sbox):
            self.inv_sbox[val] = i

        self.rcon = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]
        nk = len(self.key) // 4
        nr = nk + 6
        self.nr = nr
        w = [list(self.key[4*i:4*(i+1)]) for i in range(nk)]
        
        for i in range(nk, 4 * (nr + 1)):
            temp = list(w[i - 1])
            if i % nk == 0:
                temp = [sbox[temp[1]], sbox[temp[2]], sbox[temp[3]], sbox[temp[0]]]
                temp[0] ^= self.rcon[i // nk]
            elif nk > 6 and i % nk == 4:
                temp = [sbox[x] for x in temp]
            w.append([w[i - nk][j] ^ temp[j] for j in range(4)])
        self.round_keys = w

    def _inv_sub_bytes(self, state):
        for i in range(4):
            for j in range(4):
                state[i][j] = self.inv_sbox[state[i][j]]

    def _inv_shift_rows(self, state):
        state[1] = [state[1][3], state[1][0], state[1][1], state[1][2]]
        state[2] = [state[2][2], state[2][3], state[2][0], state[2][1]]
        state[3] = [state[3][1], state[3][2], state[3][3], state[3][0]]

    @staticmethod
    def _xtime(a):
        return ((a << 1) ^ 0x1B) & 0xFF if (a & 0x80) else (a << 1)

    def _mul(self, a, b):
        res = 0
        while b:
            if b & 1:
                res ^= a
            a = self._xtime(a)
            b >>= 1
        return res

    def _inv_mix_columns(self, state):
        for c in range(4):
            a = [state[r][c] for r in range(4)]
            state[0][c] = self._mul(0x0e, a[0]) ^ self._mul(0x0b, a[1]) ^ self._mul(0x0d, a[2]) ^ self._mul(0x09, a[3])
            state[1][c] = self._mul(0x09, a[0]) ^ self._mul(0x0e, a[1]) ^ self._mul(0x0b, a[2]) ^ self._mul(0x0d, a[3])
            state[2][c] = self._mul(0x0d, a[0]) ^ self._mul(0x09, a[1]) ^ self._mul(0x0e, a[2]) ^ self._mul(0x0b, a[3])
            state[3][c] = self._mul(0x0b, a[0]) ^ self._mul(0x0d, a[1]) ^ self._mul(0x09, a[2]) ^ self._mul(0x0e, a[3])

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

        if HAVE_CRYPTOGRAPHY:
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded) + unpadder.finalize()
            return plaintext.decode('utf-8', errors='ignore')
        else:
            cipher = PureAES(aes_key)
            decrypted = bytearray()
            prev = iv
            for i in range(0, len(ciphertext), 16):
                block = ciphertext[i:i+16]
                dec_block = cipher.decrypt_block(block)
                decrypted.extend(b ^ p for b, p in zip(dec_block, prev))
                prev = block
            pad_len = decrypted[-1]
            if pad_len < 1 or pad_len > 16:
                return None
            return decrypted[:-pad_len].decode('utf-8', errors='ignore')
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

def unpack_dean_edwards_js(packed_code):
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

def sanitize_url(url):
    if not url:
        return None
    clean = url.strip()
    clean = re.sub(r'["\'\\].*$', '', clean)
    clean = clean.replace('&amp;', '&')
    return clean

def extract_embed69_stream(imdb_id, s_num, e_num, log_dict=None):
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
                if real_link:
                    candidatos_embeds.append((srv_name, real_link))

            for dl in item.get("downloadEmbeds", []):
                srv_name = dl.get("servername", "").lower()
                link_enc = dl.get("link", "")
                real_link = descifrar_aes_cbc(link_enc, aes_key)
                if real_link:
                    candidatos_embeds.append((srv_name, real_link))

        if not candidatos_embeds:
            if log_dict is not None:
                log_dict["EMBED69_ERROR"] = "DATALINK_SIN_ENLACES"
            return None, None

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

        unpacked_js = unpack_dean_edwards_js(res_audi.text)
        search_target = unpacked_js if unpacked_js else res_audi.text

        m3u8_matches = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', search_target)
        if not m3u8_matches:
            m3u8_matches = re.findall(r'file\s*:\s*["\'](https?://[^"\']+)["\']', search_target)

        if m3u8_matches:
            clean_stream = sanitize_url(m3u8_matches[0].replace("\\/", "/"))
            return clean_stream, "https://audinifer.com/"

    except Exception as e:
        if log_dict is not None:
            log_dict["EMBED69_EXCEPTION"] = str(e)

    return None, None