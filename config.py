import os
from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.API_ID = int(getenv("API_ID", 0))
        self.API_HASH = getenv("API_HASH")

        self.BOT_TOKEN = getenv("BOT_TOKEN")
        self.MONGO_URL = getenv("MONGO_URL")

        self.LOGGER_ID = int(getenv("LOGGER_ID", 0))
        self.OWNER_ID = int(getenv("OWNER_ID", 0))

        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", 120)) * 60
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", 20))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", 20))

        self.SESSION1 = getenv("SESSION") or getenv("SESSION1", None)
        self.SESSION2 = getenv("SESSION2", None)
        self.SESSION3 = getenv("SESSION3", None)

        self.STORAGE_GROUP_ID = int(getenv("STORAGE_GROUP_ID", "-1003913556820"))
        self.STORAGE_MONGO_URL = getenv("STORAGE_MONGO_URL", "mongodb+srv://nishkarshk18_db_user:CDU2MvIT7NEwiqbN@cluster0.ozgsuzv.mongodb.net/?appName=Cluster0")
        default_vps = "http://127.0.0.1:8000" if os.path.exists("/var/music_storage") else "http://162.35.187.203:8000"
        self.VPS_STORAGE_URL = getenv("VPS_STORAGE_URL", default_vps).rstrip("/")
        self.VPS_API_KEY = getenv("VPS_API_KEY", "anku_storage_vps_key_2026")

        self.YT_API_URL = getenv("YT_API_URL") or getenv("FALLBACK_API_URL") or getenv("RAILWAY_YT_API_URL") or getenv("TITANIC_API_URL") or "https://noah-api-v3-12d3419875af.herokuapp.com"
        self.YT_API_KEY = getenv("YT_API_KEY") or getenv("FALLBACK_API_KEY") or getenv("RAILWAY_YT_API_KEY") or getenv("TITANIC_API_KEY") or "Noah-LrTinhpR67h7C_HoCGykI9wHARDRJPJVz3TwBSq6wd4"

        self.SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/titanic_network")
        self.SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/Developer_World_Advay")

        self.AUTO_LEAVE: bool = getenv("AUTO_LEAVE", "False").lower() == "true"
        self.AUTO_END: bool = getenv("AUTO_END", "True").lower() == "true"
        self.AUTOPLAY: bool = getenv("AUTOPLAY", "False").lower() == "true"
    
        self.THUMB_GEN: bool = getenv("THUMB_GEN", "True").lower() == "true"
        self.VIDEO_PLAY: bool = getenv("VIDEO_PLAY", "True").lower() == "true"
        self.STREAM_PLAY: bool = getenv("STREAM_PLAY", "True").lower() == "true"

        self.LANG_CODE = getenv("LANG_CODE", "en")

        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "").split(" ")
            if url and "batbin.me" in url
        ]
        self.DEFAULT_THUMB = getenv(
            "DEFAULT_THUMB",
            "https://i.ibb.co/gMF9J22N/Chat-GPT-Image-Oct-2-2026-at-09-34-56-AM.png",
        )
        self.PING_IMG = getenv(
            "PING_IMG",
            "assets/ping.png"
            if os.path.exists("assets/ping.png")
            else "https://i.ibb.co/rKJLsqNm/Chat-GPT-Image-Oct-2-2026-at-09-48-29-AM.png",
        )
        self.START_IMG = getenv(
            "START_IMG",
            "https://i.ibb.co/b5sr0CLv/Chat-GPT-Image-Oct-2-2026-at-09-36-30-AM.png",
        )

    def check(self):
        missing = [
            var
            for var in ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION1"]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
