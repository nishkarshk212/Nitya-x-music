# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import json
import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils


class DummyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False
        self.meta_cache_file = "cache/metadata_cache.json"
        self.tracks_cache: dict[str, dict] = {}
        self.query_cache: dict[str, str] = {}
        self._load_cache()
        self.get_cookies()
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    @staticmethod
    def get_local_path(video_id: str, video: bool = False) -> str | None:
        if not video_id:
            return None
        candidates = ["mp4"] if video else ["mp3", "webm", "m4a", "opus", "mp4"]
        for ext in candidates:
            p = f"downloads/{video_id}.{ext}"
            if Path(p).exists() and Path(p).stat().st_size > 1024:
                return p
        return None

    def _load_cache(self):
        try:
            if os.path.exists(self.meta_cache_file):
                with open(self.meta_cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tracks_cache = data.get("tracks", {})
                    self.query_cache = data.get("queries", {})
        except Exception as e:
            logger.warning(f"Failed to load metadata cache: {e}")

        try:
            downloads_dir = Path("downloads")
            if downloads_dir.exists():
                for meta_file in downloads_dir.glob("*.meta.json"):
                    try:
                        vid = meta_file.name.replace(".meta.json", "")
                        if vid not in self.tracks_cache:
                            with open(meta_file, "r", encoding="utf-8") as f:
                                meta = json.load(f)
                                self.tracks_cache[vid] = meta
                                if meta.get("title"):
                                    self.query_cache[meta["title"].lower().strip()] = vid
                    except Exception:
                        pass
        except Exception:
            pass

    def _save_cache(self):
        try:
            Path("cache").mkdir(parents=True, exist_ok=True)
            with open(self.meta_cache_file, "w", encoding="utf-8") as f:
                json.dump({"tracks": self.tracks_cache, "queries": self.query_cache}, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save metadata cache: {e}")

    def save_track_meta(self, track: Track, query: str = None):
        if not track or not getattr(track, "id", None):
            return
        meta = {
            "id": track.id,
            "title": getattr(track, "title", ""),
            "duration": getattr(track, "duration", "0:00"),
            "duration_sec": getattr(track, "duration_sec", 0),
            "thumbnail": getattr(track, "thumbnail", ""),
            "url": getattr(track, "url", f"https://www.youtube.com/watch?v={track.id}"),
            "channel_name": getattr(track, "channel_name", ""),
            "view_count": getattr(track, "view_count", ""),
            "video": getattr(track, "video", False),
        }
        self.tracks_cache[track.id] = meta
        if query:
            self.query_cache[query.lower().strip()] = track.id
        if getattr(track, "title", None):
            self.query_cache[track.title.lower().strip()] = track.id

        try:
            Path("downloads").mkdir(parents=True, exist_ok=True)
            sidecar = Path(f"downloads/{track.id}.meta.json")
            with open(sidecar, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
        except Exception:
            pass

        self._save_cache()

    def get_cached_track(self, query: str, m_id: int = 0, video: bool = False) -> Track | None:
        video_id = None
        # 1. Match direct ID or YouTube URL
        match = re.search(r"([A-Za-z0-9_-]{11})", query)
        if match and ("youtube.com" in query or "youtu.be" in query or len(query.strip()) == 11):
            potential_id = match.group(1)
            if potential_id in self.tracks_cache:
                video_id = potential_id

        # 2. Check normalized query mapping
        if not video_id:
            q_norm = query.lower().strip()
            video_id = self.query_cache.get(q_norm)

        # 3. Check title matching in cached tracks
        if not video_id:
            q_norm = query.lower().strip()
            for vid, meta in self.tracks_cache.items():
                title = meta.get("title", "").lower()
                if q_norm == title or (len(q_norm) >= 4 and q_norm in title):
                    video_id = vid
                    break

        if not video_id or video_id not in self.tracks_cache:
            return None

        # Verify the physical file is present in downloads/
        fname = self.get_local_path(video_id, video)
        if not fname:
            return None

        meta = self.tracks_cache[video_id]
        track = Track(
            id=meta["id"],
            channel_name=meta.get("channel_name", ""),
            duration=meta.get("duration", "0:00"),
            duration_sec=meta.get("duration_sec", 0),
            message_id=m_id,
            title=meta.get("title", ""),
            thumbnail=meta.get("thumbnail", ""),
            url=meta.get("url", f"https://www.youtube.com/watch?v={meta['id']}"),
            view_count=meta.get("view_count", ""),
            video=video,
            file_path=fname,
        )
        return track

    def _ensure_cookies(self):
        os.makedirs(self.cookie_dir, exist_ok=True)
        raw_b64 = os.getenv("YTDLP_COOKIES_BASE64")
        if raw_b64:
            try:
                import base64
                import gzip
                raw_bytes = base64.b64decode(raw_b64.strip())
                if raw_bytes.startswith(b"\x1f\x8b"):
                    decoded = gzip.decompress(raw_bytes).decode("utf-8", errors="ignore")
                else:
                    decoded = raw_bytes.decode("utf-8", errors="ignore")
                with open(f"{self.cookie_dir}/env_cookies.txt", "w", encoding="utf-8") as f:
                    f.write(decoded)
            except Exception as e:
                logger.warning(f"Failed to decode YTDLP_COOKIES_BASE64: {e}")

        cookie_data = os.getenv("COOKIE_DATA")
        if cookie_data:
            try:
                with open(f"{self.cookie_dir}/raw_cookies.txt", "w", encoding="utf-8") as f:
                    f.write(cookie_data.strip())
            except Exception as e:
                logger.warning(f"Failed to write COOKIE_DATA: {e}")

        if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 10:
            try:
                import shutil
                shutil.copy("cookies.txt", f"{self.cookie_dir}/root_cookies.txt")
            except Exception:
                pass

    def get_cookies(self):
        if not self.checked:
            self._ensure_cookies()
            if os.path.exists(self.cookie_dir):
                for file in sorted(os.listdir(self.cookie_dir)):
                    if file.endswith(".txt"):
                        full_path = f"{self.cookie_dir}/{file}"
                        if os.path.getsize(full_path) > 10 and full_path not in self.cookies:
                            self.cookies.append(full_path)
            self.checked = True
            logger.info(f"Loaded {len(self.cookies)} cookie file(s) for YouTube downloads.")
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        for c in self.cookies:
            if "env_cookies" in c or "cookies.txt" in c:
                return c
        return self.cookies[0]

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me/raw/" + name
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(f"{self.cookie_dir}/{name}.txt", "wb") as fw:
                        fw.write(await resp.read())
        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        cached = self.get_cached_track(query, m_id, video)
        if cached:
            logger.info(f"Instant local playback for '{query}' -> {cached.file_path}")
            return cached

        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception:
            return None
        if results and results["result"]:
            data = results["result"][0]
            track_id = data.get("id")
            file_path = self.get_local_path(track_id, video)

            track = Track(
                id=track_id,
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
            if file_path:
                track.file_path = file_path
            self.save_track_meta(track, query)
            return track
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track | None]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track_id = data.get("id")
                file_path = self.get_local_path(track_id, video)
                track = Track(
                    id=track_id,
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                if file_path:
                    track.file_path = file_path
                tracks.append(track)
        except Exception:
            pass
        return tracks

    async def get_related(
        self, video_id: str, title: str = "", video: bool = False, limit: int = 15
    ) -> list[Track]:
        tracks: list[Track] = []
        if not video_id and not title:
            return tracks

        # Strategy 1: YouTube Innertube /youtubei/v1/next endpoint
        if video_id:
            try:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                }
                payload = {
                    "context": {
                        "client": {
                            "clientName": "WEB",
                            "clientVersion": "2.20240101.00.00",
                            "hl": "en",
                            "gl": "IN",
                        }
                    },
                    "videoId": video_id,
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://www.youtube.com/youtubei/v1/next",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=8),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results = (
                                data.get("contents", {})
                                .get("twoColumnWatchNextResults", {})
                                .get("secondaryResults", {})
                                .get("secondaryResults", {})
                                .get("results", [])
                            )
                            for item in results:
                                cid = None
                                t_title = None
                                dur = "0:00"
                                channel = ""
                                thumb_url = None

                                if "lockupViewModel" in item:
                                    vm = item["lockupViewModel"]
                                    cid = vm.get("contentId")
                                    meta = vm.get("metadata", {}).get("lockupMetadataViewModel", {})
                                    t_title = meta.get("title", {}).get("content")
                                    rows = meta.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
                                    if rows and rows[0].get("metadataParts"):
                                        channel = rows[0]["metadataParts"][0].get("text", {}).get("content", "")
                                    for o in vm.get("contentImage", {}).get("thumbnailViewModel", {}).get("overlays", []):
                                        badges = o.get("thumbnailBottomOverlayViewModel", {}).get("badges", [])
                                        for b in badges:
                                            t = b.get("thumbnailBadgeViewModel", {}).get("text")
                                            if t:
                                                dur = t
                                                break
                                        if dur != "0:00":
                                            break
                                    thumb_url = f"https://i.ytimg.com/vi/{cid}/hqdefault.jpg"

                                elif "compactVideoRenderer" in item:
                                    cvr = item["compactVideoRenderer"]
                                    cid = cvr.get("videoId")
                                    title_dict = cvr.get("title", {})
                                    t_title = title_dict.get("simpleText") or (
                                        title_dict.get("runs", [{}])[0].get("text") if title_dict.get("runs") else ""
                                    )
                                    dur = cvr.get("lengthText", {}).get("simpleText", "0:00")
                                    channel = cvr.get("shortBylineText", {}).get("runs", [{}])[0].get("text", "")
                                    thumb_url = f"https://i.ytimg.com/vi/{cid}/hqdefault.jpg"

                                if cid and t_title and cid != video_id and len(cid) == 11 and not cid.startswith(("RD", "PL")):
                                    try:
                                        dur_sec = utils.to_seconds(dur)
                                    except Exception:
                                        dur_sec = 0
                                    if dur_sec < 10:
                                        continue
                                    file_path = self.get_local_path(cid, video)
                                    trk = Track(
                                        id=cid,
                                        channel_name=channel,
                                        duration=dur,
                                        duration_sec=dur_sec,
                                        title=t_title[:25],
                                        thumbnail=thumb_url,
                                        url=f"https://www.youtube.com/watch?v={cid}",
                                        user="˹ᴧᴜᴛᴏᴘʟᴧʏ˼ 📻",
                                        video=video,
                                        file_path=file_path,
                                    )
                                    tracks.append(trk)
                                    if len(tracks) >= limit:
                                        break
            except Exception as e:
                logger.warning(f"Innertube related error: {e}")

        # Strategy 2: VideosSearch fallback
        if not tracks and title:
            try:
                query = f"{title} song"
                _search = VideosSearch(query, limit=limit, with_live=False)
                res = await _search.next()
                if res and res.get("result"):
                    for data in res["result"]:
                        cid = data.get("id")
                        if not cid or cid == video_id:
                            continue
                        dur = data.get("duration", "0:00")
                        try:
                            dur_sec = utils.to_seconds(dur)
                        except Exception:
                            dur_sec = 0
                        ext = "mp4" if video else "webm"
                        file_path = self.get_local_path(cid, video)
                        trk = Track(
                            id=cid,
                            channel_name=data.get("channel", {}).get("name", ""),
                            duration=dur,
                            duration_sec=dur_sec,
                            title=data.get("title", "")[:25],
                            thumbnail=data.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
                            url=data.get("link"),
                            user="˹ᴧᴜᴛᴏᴘʟᴧʏ˼ 📻",
                            video=video,
                            file_path=file_path,
                        )
                        tracks.append(trk)
                        if len(tracks) >= limit:
                            break
            except Exception as e:
                logger.warning(f"VideosSearch related fallback error: {e}")

        return tracks

    async def download(
        self, video_id: str, video: bool = False, title: str = "", duration: int = 0
    ) -> str | None:
        from anony.core.storage import storage_engine
        from anony import config

        target_path = f"downloads/{video_id}.mp4" if video else f"downloads/{video_id}.mp3"

        # =========================================================================
        # PROCESS 1: Old song direct from local disk or 1TB VPS storage
        # =========================================================================
        # 1a. Local disk cache hit
        for cand_ext in (["mp4"] if video else ["mp3", "webm", "m4a", "opus", "mp4"]):
            cand_p = f"downloads/{video_id}.{cand_ext}"
            if Path(cand_p).exists() and Path(cand_p).stat().st_size > 1024:
                logger.info(f"[PROCESS 1: LOCAL DISK] Instant hit: {video_id} -> {cand_p}")
                return cand_p

        # 1b. 1TB VPS Music Storage Engine (instant restore from VPS NVMe storage)
        if await storage_engine.download_from_vps(video_id, target_path, is_video=video):
            logger.info(f"[PROCESS 1: VPS STORAGE] Restored old song: {video_id} -> {target_path}")
            return target_path

        # 1c. Telegram Dump Supergroup (-1003913556820)
        if await storage_engine.restore_from_telegram_dump(video_id, target_path, is_video=video):
            logger.info(f"[PROCESS 1: TG DUMP] Restored old song: {video_id} -> {target_path}")
            return target_path

        # =========================================================================
        # PROCESS 2: New song -> Live download by Dedicated API
        # =========================================================================
        primary_url = getattr(config, "YT_API_URL", None)
        primary_key = getattr(config, "YT_API_KEY", None)

        if not video and primary_url and primary_key:
            res = await self._live_download_api(video_id, primary_url, primary_key)
            if res and Path(res).exists() and Path(res).stat().st_size > 1024:
                self._persist_song(res, video_id, title, duration, video)
                return res

            # =====================================================================
            # PROCESS 3: New song -> Download complete by Dedicated API (after live fail)
            # =====================================================================
            res = await self._complete_download_api(video_id, primary_url, primary_key)
            if res and Path(res).exists() and Path(res).stat().st_size > 1024:
                self._persist_song(res, video_id, title, duration, video)
                return res

        # =========================================================================
        # PROCESS 4: Failover API Pool & Local yt-dlp Extractor
        # =========================================================================
        if not video:
            res = await self._download_via_fallback_api_pool(video_id)
            if res and Path(res).exists() and Path(res).stat().st_size > 1024:
                self._persist_song(res, video_id, title, duration, video)
                return res

        # Local yt-dlp extractor fallback
        res = await self._download_via_ytdlp(video_id, video=video)
        if res and Path(res).exists() and Path(res).stat().st_size > 1024:
            self._persist_song(res, video_id, title, duration, video)
            return res

        return None

    def _persist_song(self, file_path: str, video_id: str, title: str = "", duration: int = 0, is_video: bool = False):
        from anony.core.storage import storage_engine
        t_title = title or self.tracks_cache.get(video_id, {}).get("title", "")
        t_dur = duration or self.tracks_cache.get(video_id, {}).get("duration_sec", 0)
        storage_engine.persist_background(
            file_path=file_path,
            video_id=video_id,
            title=t_title,
            duration=t_dur,
            is_video=is_video,
        )
        if video_id in self.tracks_cache:
            try:
                sidecar = Path(f"downloads/{video_id}.meta.json")
                if not sidecar.exists():
                    with open(sidecar, "w", encoding="utf-8") as f:
                        json.dump(self.tracks_cache[video_id], f, ensure_ascii=False)
            except Exception:
                pass

    async def _live_download_api(self, video_id: str, base_url: str, api_key: str) -> str | None:
        """Process 2: Live download proxy stream from dedicated API."""
        base_url = base_url.rstrip("/")
        out_file = f"downloads/{video_id}.mp3"
        stream_url = f"{base_url}/stream/audio?id={video_id}&api_key={api_key}"
        headers = {"x-api-key": api_key, "User-Agent": "Chips-Music/3.0"}
        try:
            dl_timeout = aiohttp.ClientTimeout(connect=15, sock_read=90, total=300)
            async with aiohttp.ClientSession() as session:
                async with session.get(stream_url, headers=headers, timeout=dl_timeout, allow_redirects=True) as dl_resp:
                    if dl_resp.status in (200, 206):
                        Path("downloads").mkdir(parents=True, exist_ok=True)
                        tmp_out = f"{out_file}.tmp"
                        with open(tmp_out, "wb") as f:
                            async for chunk in dl_resp.content.iter_chunked(256 * 1024):
                                f.write(chunk)
                        if Path(tmp_out).exists() and Path(tmp_out).stat().st_size > 1024:
                            os.replace(tmp_out, out_file)
                            logger.info(
                                f"[PROCESS 2: LIVE STREAM DOWNLOAD] Cached {video_id} via dedicated API {base_url} -> {out_file} ({Path(out_file).stat().st_size} bytes)"
                            )
                            return out_file
        except Exception as e:
            logger.warning(f"[PROCESS 2 FAIL] Stream download via dedicated API {base_url} failed for {video_id}: {e}")
        return None

    async def _complete_download_api(self, video_id: str, base_url: str, api_key: str) -> str | None:
        """Process 3: Complete download (100% cached audio file) from dedicated API."""
        base_url = base_url.rstrip("/")
        out_file = f"downloads/{video_id}.mp3"
        complete_url = f"{base_url}/download/complete?id={video_id}"
        headers = {"x-api-key": api_key, "User-Agent": "Chips-Music/3.0"}
        try:
            dl_timeout = aiohttp.ClientTimeout(connect=10, sock_read=60, total=300)
            async with aiohttp.ClientSession() as session:
                async with session.get(complete_url, headers=headers, timeout=dl_timeout) as dl_resp:
                    if dl_resp.status == 200:
                        Path("downloads").mkdir(parents=True, exist_ok=True)
                        tmp_out = f"{out_file}.tmp"
                        with open(tmp_out, "wb") as f:
                            async for chunk in dl_resp.content.iter_chunked(256 * 1024):
                                f.write(chunk)
                        if Path(tmp_out).exists() and Path(tmp_out).stat().st_size > 1024:
                            os.replace(tmp_out, out_file)
                            logger.info(
                                f"[PROCESS 3: COMPLETE DOWNLOAD] Restored {video_id} via dedicated API {base_url} -> {out_file} ({Path(out_file).stat().st_size} bytes)"
                            )
                            return out_file
        except Exception as e:
            logger.warning(f"[PROCESS 3 FAIL] Complete download via dedicated API {base_url} failed for {video_id}: {e}")
        return None

    async def _download_via_fallback_api_pool(self, video_id: str) -> str | None:
        """Process 4a: Failover API pool (trying other active fleet APIs)."""
        from anony import config
        primary_url = (getattr(config, "YT_API_URL", None) or "").rstrip("/")
        api_pool = [
            {"name": "Noah", "url": "https://noah-api-v3-12d3419875af.herokuapp.com", "key": "Noah-LrTinhpR67h7C_HoCGykI9wHARDRJPJVz3TwBSq6wd4"},
            {"name": "Titanic", "url": "https://titanic-api-v3-01462a8481af.herokuapp.com", "key": "titanic_lhQkzaBhIQTwpquq_XBIfBI52wtN49fhdTOBBBkfLNo"},
            {"name": "Panda", "url": "https://panda-api-v3-6e9434966ef9.herokuapp.com", "key": "panda_qpyudLY8bF8rFt69yK-fbLU5wQSO1nHK9H4GixjYNTY"},
            {"name": "APIHub", "url": "https://apihub-v3-9d48fbce0605.herokuapp.com", "key": "lily_mOVOd9TG7zuE4L9QDxEndbiyjQc9he"},
            {"name": "PublicAPI", "url": "https://publicapi-v3-d949abed7191.herokuapp.com", "key": "lily_mOVOd9TG7zuE4L9QDxEndbiyjQc9he"},
            {"name": "APIKey", "url": "https://apikey-v3-1854882f97a1.herokuapp.com", "key": "lily_mOVOd9TG7zuE4L9QDxEndbiyjQc9he"},
            {"name": "FastAPI", "url": "https://fast-api-v3-b7014eeb7106.herokuapp.com", "key": "fastapi_2PifF1fuHEYA11VVpxT0keDnf-MhovkIaCbiDqXrUK0"},
        ]
        for item in api_pool:
            c_url = item["url"].rstrip("/")
            if c_url == primary_url:
                continue
            # Try complete download first on backup
            res = await self._complete_download_api(video_id, c_url, item["key"])
            if res:
                return res
            # Try live download fallback on backup
            res = await self._live_download_api(video_id, c_url, item["key"])
            if res:
                return res
        return None

    async def _download_via_ytdlp(self, video_id: str, video: bool = False) -> str | None:
        """Process 4b: Local yt-dlp extractor fallback."""
        url = self.base + video_id
        cookie = self.get_cookies()
        base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "logger": DummyLogger(),
            "nocheckcertificate": True,
            "cookiefile": cookie,
            "remote_components": ["ejs:github"],
            "extractor_args": {
                "youtube": {
                    "player_client": ["tv", "mweb", "android", "ios", "web_embedded"],
                    "player_skip": ["webpage", "configs"],
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        if video:
            ydl_opts = {
                **base_opts,
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio)/best[height<=?720]/best",
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                "format": "bestaudio/best",
            }

        def _exec():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([url])
                    for candidate_ext in ["webm", "mp4", "m4a", "opus", "mp3"]:
                        candidate_path = f"downloads/{video_id}.{candidate_ext}"
                        if Path(candidate_path).exists() and Path(candidate_path).stat().st_size > 1024:
                            logger.info(f"[PROCESS 4: YT-DLP] Downloaded: {video_id} -> {candidate_path}")
                            return candidate_path
                    return None
                except Exception as ex:
                    logger.warning(f"Local yt-dlp failed for {video_id}: {ex}")
                    return None

        return await asyncio.to_thread(_exec)

    async def get_stream_url(self, video_id: str, video: bool = False) -> str | None:
        return self.get_local_path(video_id, video)


