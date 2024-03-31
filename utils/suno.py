import json
import re
import time
from datetime import datetime
from http.cookies import SimpleCookie

from curl_cffi import requests
from curl_cffi.requests import Cookies

from utils.logger import FileSplitLogger

ua = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/122.0.0.0 Safari/537.36"
)

get_session_url = "https://clerk.suno.ai/v1/client?_clerk_js_version=4.70.5"
exchange_token_url = (
    "https://clerk.suno.ai/v1/client/sessions/{sid}/tokens?_clerk_js_version=4.70.5"
)

base_url = "https://app.suno.ai"
browser_version = "edge101"

HEADERS = {
    "Origin": base_url,
    "Referer": base_url + "/",
    "DNT": "1",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "TE": "trailers",
    "User-Agent": ua,
}

suno_logger = FileSplitLogger("./logs/suno.log").logger


class SongsGen:
    def __init__(self, cookie: str) -> None:
        self.session: requests.Session = requests.Session()
        HEADERS["user-agent"] = ua
        self.cookie = cookie
        self.session.cookies = self.parse_cookie_string(self.cookie)
        auth_token = self._get_auth_token()
        HEADERS["Authorization"] = f"Bearer {auth_token}"
        self.session.headers = HEADERS
        self.sid = None

    def _get_auth_token(self):
        response = self.session.get(get_session_url, impersonate=browser_version)
        data = response.json()
        r = data.get("response")
        sid = None
        if r:
            sid = r.get("last_active_session_id")
        if not sid:
            suno_logger.warning("Failed to get session id")
            raise Exception("Failed to get session id")
        self.sid = sid
        response = self.session.post(
            exchange_token_url.format(sid=sid), impersonate=browser_version
        )
        data = response.json()
        return data.get("jwt")

    def get_session_expire_date(self) -> [datetime, None]:
        # for Setting both the 'Origin' and 'Authorization' headers is forbidden
        origin = None
        if "Origin" in self.session.headers:
            origin = self.session.headers.pop("Origin")
        response = self.session.get(get_session_url, impersonate=browser_version)
        if origin:
            self.session.headers["Origin"] = origin
        data = response.json()
        # suno_logger.info("get_session_expire_date data: %s", data)
        r = data.get("response")
        if r and r.get("sessions"):
            sessions = r.get("sessions")[0]
            expire_at = sessions.get("expire_at")
            return datetime.fromtimestamp(int(expire_at) / 1000)

    def _renew(self):
        origin = None
        if 'Origin' in self.session.headers:
            origin = self.session.headers.pop('Origin')
        response = self.session.post(
            exchange_token_url.format(sid=self.sid), impersonate=browser_version
        )
        if origin:
            self.session.headers['Origin'] = origin
        resp = response.json()
        if "jwt" in resp.keys():
            self.session.headers["Authorization"] = f"Bearer {resp.get('jwt')}"
        else:
            suno_logger.warning("renew no jwt in resp, with resp: %s", resp)

    @staticmethod
    def parse_cookie_string(cookie_string):
        cookie = SimpleCookie()
        cookie.load(cookie_string)
        cookies_dict = {}
        for key, morsel in cookie.items():
            cookies_dict[key] = morsel.value
        return Cookies(cookies_dict)

    def get_limit_left(self) -> int:
        self.session.headers["user-agent"] = ua
        r = self.session.get(
            "https://studio-api.suno.ai/api/billing/info/", impersonate=browser_version
        )
        return int(r.json()["total_credits_left"] / 10)

    def _fetch_songs_metadata(self, ids, retry_count=0, max_retries=6):
        id1, id2 = ids[:2]
        rs = {"song_name": "", "lyric": "", "song_ids": []}
        url = f"https://studio-api.suno.ai/api/feed/?ids={id1}%2C{id2}"
        response = self.session.get(url, impersonate=browser_version)
        try:
            data = response.json()
            for d in data:
                if len(rs["song_ids"]) != 2 and (s_id := d.get("id")):
                    rs["song_ids"].append(s_id)
                mt = d.get("metadata")
                if not rs["lyric"] and isinstance(mt, dict):
                    rs["lyric"] = re.sub(r"\[.*?\]", "", mt.get("prompt"))
                if not rs["song_name"] and d.get("title"):
                    rs["song_name"] = d.get("title")
            if all(rs.values()):
                rs["lyric"] = rs["song_name"] + "\n\n" + rs["lyric"]
                return rs
            else:
                time.sleep(10)
                return self._fetch_songs_metadata(ids, retry_count)
        except Exception as e:
            suno_logger.warning("fetch songs metadata exception: %s", e)
            self._renew()
            time.sleep(2)
            return self._fetch_songs_metadata(ids, retry_count + 1, max_retries)

    def get_songs_info(self, prompt: str) -> dict:
        url = "https://studio-api.suno.ai/api/generate/v2/"
        self.session.headers["user-agent"] = ua
        payload = {
            "gpt_description_prompt": prompt,
            "mv": "chirp-v3-0",
            "prompt": "",
            "make_instrumental": False,
        }
        response = self.session.post(
            url,
            data=json.dumps(payload),
            impersonate=browser_version,
        )
        if not response.ok:
            suno_logger.error("response.text", response.text)
            raise Exception(f"Error response {str(response)}")
        response_body = response.json()
        songs_meta_info = response_body["clips"]
        request_ids = [i["id"] for i in songs_meta_info]
        return self._fetch_songs_metadata(request_ids)
