import argparse
import json
import os
import re
import time
from datetime import datetime
from http.cookies import SimpleCookie
from pathlib import Path

from curl_cffi import requests
from curl_cffi.requests import Cookies
from requests import get as rget
from rich import print

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
            raise Exception("Failed to get session id")
        self.sid = sid
        response = self.session.post(
            exchange_token_url.format(sid=sid), impersonate=browser_version
        )
        data = response.json()
        return data.get("jwt")

    def get_session_expire_date(self):
        response = self.session.get(get_session_url, impersonate=browser_version)
        data = response.json()
        r = data.get("response")
        if r and r.get("sessions"):
            sessions = r.get("sessions")[0]
            expire_at = sessions.get("expire_at")
            return datetime.fromtimestamp(int(expire_at) / 1000).strftime(
                "%Y-%m-%d %H:%m:%S"
            )

    def _renew(self):
        response = self.session.post(
            exchange_token_url.format(sid=self.sid), impersonate=browser_version
        )
        resp = response.json()
        if "jwt" in resp.keys():
            self.session.headers["Authorization"] = f"Bearer {resp.get('jwt')}"
        else:
            print("renew no jwt in resp:")
            print(f"resp:{resp}")

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

    def _fetch_songs_metadata(self, ids):
        id1, id2 = ids[:2]
        rs = {"song_name": "", "lyric": "", "song_urls": []}
        url = f"https://studio-api.suno.ai/api/feed/?ids={id1}%2C{id2}"
        response = self.session.get(url, impersonate=browser_version)
        try:
            data = response.json()
            print("get data", data)
            for d in data:
                if len(rs["song_urls"]) != 2 and (s_id := d.get("id")):
                    rs["song_urls"].append(f"https://audiopipe.suno.ai/?item_id={s_id}")
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
                return self._fetch_songs_metadata(ids)
        except Exception as e:
            print("fetch songs metadata exception:", e)
            self._renew()
            time.sleep(5)
            return self._fetch_songs_metadata(ids)

    def get_songs(self, prompt: str) -> dict:
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
            print("response.text", response.text)
            raise Exception(f"Error response {str(response)}")
        response_body = response.json()
        songs_meta_info = response_body["clips"]
        request_ids = [i["id"] for i in songs_meta_info]
        print("Waiting for results...")
        return self._fetch_songs_metadata(request_ids)

    def save_songs(
        self,
        prompt: str,
        output_dir: str = "./output",
    ):
        try:
            song_info_dict = self.get_songs(prompt)  # make the info dict
            song_name = song_info_dict["song_name"].replace(" ", "_")
            lyric = song_info_dict["lyric"]
            song_urls = song_info_dict["song_urls"]
        except Exception as e:
            print(f"get song info failed  with {e}")
            raise
        if not Path(output_dir).exists():
            Path(output_dir).mkdir()
        if len(song_urls) == 0:
            print("get failed")
            return None, None
        # only download the first one
        time.sleep(10)  # wait for the song to be ready, maybe need more time
        response = rget(song_urls[0], allow_redirects=False, stream=True)
        if response.status_code != 200:
            raise Exception("Could not download song")
        # save response to file
        song_file = Path(output_dir) / f"{song_name}.mp3"
        with open(song_file, "wb") as output_file:
            for chunk in response.iter_content(chunk_size=1024):
                # If the chunk is not empty, write it to the file.
                if chunk:
                    output_file.write(chunk)
            print(f"downloaded {song_name} finished")
        return song_file.absolute(), lyric, song_name, song_urls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-U", help="Auth cookie from browser", type=str, default="")
    parser.add_argument(
        "--prompt",
        help="Prompt to generate songs for",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        help="Output directory",
        type=str,
        default="./output",
    )

    args = parser.parse_args()

    # Create song generator
    # follow old style
    song_generator = SongsGen(
        os.environ.get("SUNO_COOKIE") or args.U,
    )
    print(f"{song_generator.get_limit_left()} songs left")
    song_generator.save_songs(
        prompt=args.prompt,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
