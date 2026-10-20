# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from random import randint
from time import time

from pymongo import AsyncMongoClient

from anony import config, logger, userbot


class MongoDB:
    def __init__(self):
        """
        Initialize the MongoDB connection.
        """
        import certifi
        self.mongo = AsyncMongoClient(config.MONGO_URL, serverSelectionTimeoutMS=12500, tlsCAFile=certifi.where())
        self.db = self.mongo.Yukki

        storage_url = config.STORAGE_MONGO_URL or config.MONGO_URL
        self.storage_mongo = AsyncMongoClient(storage_url, serverSelectionTimeoutMS=12500, tlsCAFile=certifi.where())
        self.storage_db = self.storage_mongo.SharedStorage
        self.music_cachedb = self.storage_db.music_cache

        self.admin_list = {}
        self.active_calls = {}
        self.admin_play = []
        self.blacklisted = []
        self.cmd_delete = []
        self.loop = {}
        self.notified = []
        self.cache = self.db.cache
        self.logger = False

        self.assistant = {}
        self.assistantdb = self.db.assistant

        self.auth = {}
        self.authdb = self.db.auth

        self.chats = []
        self.chatsdb = self.db.chats

        self.lang = {}
        self.langdb = self.db.lang

        self.users = []
        self.usersdb = self.db.users

        self.songsdb = self.db.songs
        self.autoplay = {}
        self.autoplaydb = self.db.autoplay
        self.welcome = {}
        self.welcomedb = self.db.welcome
        self.vc_notify = {}
        self.vc_notifydb = self.db.vc_notify
        self.play_thumb = {}
        self.play_thumbdb = self.db.play_thumb

    async def connect(self) -> None:
        """Check if we can connect to the database.

        Raises:
            SystemExit: If the connection to the database fails.
        """
        try:
            start = time()
            await self.mongo.admin.command("ping")
            logger.info(f"Database connection successful. ({time() - start:.2f}s)")
            await self.load_cache()
        except Exception as e:
            raise SystemExit(f"Database connection failed: {type(e).__name__}") from e

    async def close(self) -> None:
        """Close the connection to the database."""
        await self.mongo.close()
        try:
            await self.storage_mongo.close()
        except Exception:
            pass
        logger.info("Database connection closed.")

    # CACHE
    async def get_call(self, chat_id: int) -> bool:
        return chat_id in self.active_calls

    async def add_call(self, chat_id: int) -> None:
        self.active_calls[chat_id] = 1

    async def remove_call(self, chat_id: int) -> None:
        self.active_calls.pop(chat_id, None)

    async def playing(self, chat_id: int, paused: bool = None) -> bool | None:
        if paused is not None:
            self.active_calls[chat_id] = int(not paused)
        return bool(self.active_calls.get(chat_id, 0))

    async def get_admins(self, chat_id: int, reload: bool = False) -> list[int]:
        from anony.helpers._admins import reload_admins

        if chat_id not in self.admin_list or reload:
            self.admin_list[chat_id] = await reload_admins(chat_id)
        return self.admin_list[chat_id]

    async def get_loop(self, chat_id: int) -> int:
        return self.loop.get(chat_id, 0)

    async def set_loop(self, chat_id: int, count: int) -> None:
        self.loop[chat_id] = count

    async def is_autoplay(self, chat_id: int) -> bool:
        if chat_id not in self.autoplay:
            doc = await self.autoplaydb.find_one({"_id": chat_id})
            if doc is not None:
                self.autoplay[chat_id] = doc.get("status", True)
            else:
                self.autoplay[chat_id] = config.AUTOPLAY
        return self.autoplay[chat_id]

    async def set_autoplay(self, chat_id: int, status: bool) -> None:
        self.autoplay[chat_id] = status
        await self.autoplaydb.update_one(
            {"_id": chat_id},
            {"$set": {"status": status}},
            upsert=True,
        )

    # WELCOME METHODS
    async def is_welcome(self, chat_id: int) -> bool:
        if not hasattr(self, "welcome"):
            self.welcome = {}
            self.welcomedb = self.db.welcome
        if chat_id not in self.welcome:
            doc = await self.welcomedb.find_one({"_id": chat_id})
            if doc is not None:
                self.welcome[chat_id] = doc.get("status", True)
            else:
                self.welcome[chat_id] = True
        return self.welcome[chat_id]

    async def set_welcome(self, chat_id: int, status: bool) -> None:
        if not hasattr(self, "welcome"):
            self.welcome = {}
            self.welcomedb = self.db.welcome
        self.welcome[chat_id] = status
        await self.welcomedb.update_one(
            {"_id": chat_id},
            {"$set": {"status": status}},
            upsert=True,
        )

    # VC NOTIFY METHODS
    async def is_vc_notify(self, chat_id: int) -> bool:
        if not hasattr(self, "vc_notify"):
            self.vc_notify = {}
            self.vc_notifydb = self.db.vc_notify
        if chat_id not in self.vc_notify:
            doc = await self.vc_notifydb.find_one({"_id": chat_id})
            if doc is not None:
                self.vc_notify[chat_id] = doc.get("status", True)
            else:
                self.vc_notify[chat_id] = True
        return self.vc_notify[chat_id]

    async def set_vc_notify(self, chat_id: int, status: bool) -> None:
        if not hasattr(self, "vc_notify"):
            self.vc_notify = {}
            self.vc_notifydb = self.db.vc_notify
        self.vc_notify[chat_id] = status
        await self.vc_notifydb.update_one(
            {"_id": chat_id},
            {"$set": {"status": status}},
            upsert=True,
        )

    # PLAY THUMBNAIL METHODS
    async def is_play_thumb(self, chat_id: int) -> bool:
        if not hasattr(self, "play_thumb"):
            self.play_thumb = {}
            self.play_thumbdb = self.db.play_thumb
        if chat_id not in self.play_thumb:
            doc = await self.play_thumbdb.find_one({"_id": chat_id})
            if doc is not None:
                self.play_thumb[chat_id] = doc.get("status", True)
            else:
                self.play_thumb[chat_id] = True
        return self.play_thumb[chat_id]

    async def set_play_thumb(self, chat_id: int, status: bool) -> None:
        if not hasattr(self, "play_thumb"):
            self.play_thumb = {}
            self.play_thumbdb = self.db.play_thumb
        self.play_thumb[chat_id] = status
        await self.play_thumbdb.update_one(
            {"_id": chat_id},
            {"$set": {"status": status}},
            upsert=True,
        )

    # AUTH METHODS
    async def _get_auth(self, chat_id: int) -> set[int]:
        if chat_id not in self.auth:
            doc = await self.authdb.find_one({"_id": chat_id}) or {}
            self.auth[chat_id] = set(doc.get("user_ids", []))
        return self.auth[chat_id]

    async def is_auth(self, chat_id: int, user_id: int) -> bool:
        return user_id in await self._get_auth(chat_id)

    async def add_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id not in users:
            users.add(user_id)
            await self.authdb.update_one(
                {"_id": chat_id}, {"$addToSet": {"user_ids": user_id}}, upsert=True
            )

    async def rm_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id in users:
            users.discard(user_id)
            await self.authdb.update_one(
                {"_id": chat_id}, {"$pull": {"user_ids": user_id}}
            )

    # ASSISTANT METHODS
    async def set_assistant(self, chat_id: int) -> int:
        num = randint(1, len(userbot.clients))
        await self.assistantdb.update_one(
            {"_id": chat_id},
            {"$set": {"num": num}},
            upsert=True,
        )
        self.assistant[chat_id] = num
        return num

    async def get_assistant(self, chat_id: int):
        from anony import anon

        if chat_id not in self.assistant:
            doc = await self.assistantdb.find_one({"_id": chat_id})
            num = doc["num"] if doc else None

            if not num or num > len(anon.clients):
                num = await self.set_assistant(chat_id)
            self.assistant[chat_id] = num

        return anon.clients[self.assistant[chat_id] - 1]

    async def get_client(self, chat_id: int):
        if chat_id not in self.assistant:
            await self.get_assistant(chat_id)

        num = self.assistant[chat_id]
        if num > len(userbot.clients):
            num = await self.set_assistant(chat_id)
            self.assistant[chat_id] = num

        return {1: userbot.one, 2: userbot.two, 3: userbot.three}.get(num)

    # BLACKLIST METHODS
    async def add_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            self.blacklisted.append(chat_id)
            return await self.cache.update_one(
                {"_id": "bl_chats"},
                {"$addToSet": {"chat_ids": chat_id}},
                upsert=True,
            )
        await self.cache.update_one(
            {"_id": "bl_users"},
            {"$addToSet": {"user_ids": chat_id}},
            upsert=True,
        )

    async def del_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            self.blacklisted.remove(chat_id)
            return await self.cache.update_one(
                {"_id": "bl_chats"},
                {"$pull": {"chat_ids": chat_id}},
            )
        await self.cache.update_one(
            {"_id": "bl_users"},
            {"$pull": {"user_ids": chat_id}},
        )

    async def get_blacklisted(self, chat: bool = False) -> list[int]:
        if chat:
            if not self.blacklisted:
                doc = await self.cache.find_one({"_id": "bl_chats"})
                self.blacklisted.extend(doc.get("chat_ids", []) if doc else [])
            return self.blacklisted
        doc = await self.cache.find_one({"_id": "bl_users"})
        return doc.get("user_ids", []) if doc else []

    # CHAT METHODS
    async def is_chat(self, chat_id: int) -> bool:
        if not self.chats:
            await self.get_chats()
        return chat_id in self.chats

    async def add_chat(self, chat_id: int) -> None:
        if not await self.is_chat(chat_id):
            self.chats.append(chat_id)
            await self.chatsdb.update_one(
                {"_id": chat_id},
                {"$set": {"_id": chat_id}},
                upsert=True,
            )

    async def rm_chat(self, chat_id: int) -> None:
        if await self.is_chat(chat_id):
            self.chats.remove(chat_id)
            await self.chatsdb.delete_one({"_id": chat_id})

    async def get_chats(self) -> list:
        chats = set(self.chats)
        try:
            async for chat in self.chatsdb.find():
                cid = chat.get("_id") if chat.get("_id") is not None else chat.get("chat_id")
                if cid is not None:
                    try:
                        chats.add(int(cid))
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.warning("Error fetching chatsdb: %s", e)
        try:
            async for chat in self.mongo.Anon.chats.find():
                cid = chat.get("_id") if chat.get("_id") is not None else chat.get("chat_id")
                if cid is not None:
                    try:
                        chats.add(int(cid))
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass
        self.chats = list(chats)
        return self.chats

    # COMMAND DELETE
    async def get_cmd_delete(self, chat_id: int) -> bool:
        if chat_id not in self.cmd_delete:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("cmd_delete"):
                self.cmd_delete.append(chat_id)
        return chat_id in self.cmd_delete

    async def set_cmd_delete(self, chat_id: int, delete: bool = False) -> None:
        if delete:
            self.cmd_delete.append(chat_id)
        else:
            self.cmd_delete.remove(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"cmd_delete": delete}},
            upsert=True,
        )

    # LANGUAGE METHODS
    async def set_lang(self, chat_id: int, lang_code: str):
        await self.langdb.update_one(
            {"_id": chat_id},
            {"$set": {"lang": lang_code}},
            upsert=True,
        )
        self.lang[chat_id] = lang_code

    async def get_lang(self, chat_id: int) -> str:
        if chat_id not in self.lang:
            doc = await self.langdb.find_one({"_id": chat_id})
            self.lang[chat_id] = doc["lang"] if doc else config.LANG_CODE
        return self.lang[chat_id]

    # LOGGER METHODS
    async def is_logger(self) -> bool:
        return self.logger

    async def get_logger(self) -> bool:
        doc = await self.cache.find_one({"_id": "logger"})
        if doc:
            self.logger = doc["status"]
        return self.logger

    async def set_logger(self, status: bool) -> None:
        self.logger = status
        await self.cache.update_one(
            {"_id": "logger"},
            {"$set": {"status": status}},
            upsert=True,
        )

    # PLAY MODE METHODS
    async def get_play_mode(self, chat_id: int) -> bool:
        if chat_id not in self.admin_play:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("admin_play"):
                self.admin_play.append(chat_id)
        return chat_id in self.admin_play

    async def set_play_mode(self, chat_id: int, remove: bool = False) -> None:
        if remove and chat_id in self.admin_play:
            self.admin_play.remove(chat_id)
        else:
            self.admin_play.append(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"admin_play": not remove}},
            upsert=True,
        )

    # SUDO METHODS
    async def add_sudo(self, user_id: int) -> None:
        await self.cache.update_one(
            {"_id": "sudoers"}, {"$addToSet": {"user_ids": user_id}}, upsert=True
        )

    async def del_sudo(self, user_id: int) -> None:
        await self.cache.update_one(
            {"_id": "sudoers"}, {"$pull": {"user_ids": user_id}}
        )

    async def get_sudoers(self) -> list[int]:
        doc = await self.cache.find_one({"_id": "sudoers"})
        return doc.get("user_ids", []) if doc else []

    # USER METHODS
    async def is_user(self, user_id: int) -> bool:
        if not self.users:
            await self.get_users()
        return user_id in self.users

    async def add_user(self, user_id: int) -> None:
        if not await self.is_user(user_id):
            self.users.append(user_id)
            await self.usersdb.update_one(
                {"_id": user_id},
                {"$set": {"_id": user_id}},
                upsert=True,
            )

    async def rm_user(self, user_id: int) -> None:
        if await self.is_user(user_id):
            self.users.remove(user_id)
            await self.usersdb.delete_one({"_id": user_id})

    async def get_users(self) -> list:
        users = set(self.users)
        try:
            async for user in self.usersdb.find():
                uid = user.get("_id") if user.get("_id") is not None else user.get("user_id")
                if uid is not None:
                    try:
                        users.add(int(uid))
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.warning("Error fetching usersdb: %s", e)
        try:
            async for user in self.mongo.Anon.users.find():
                uid = user.get("_id") if user.get("_id") is not None else user.get("user_id")
                if uid is not None:
                    try:
                        users.add(int(uid))
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass
        self.users = list(users)
        return self.users

    async def migrate_coll(self) -> None:
        logger.info("Syncing users and chats from legacy and secondary collections...")
        try:
            async for user in self.db.tgusersdb.find():
                _id = user.get("_id")
                uid = _id if isinstance(_id, int) else int(user.get("user_id", 0))
                if uid:
                    await self.usersdb.update_one({"_id": uid}, {"$set": {"_id": uid}}, upsert=True)
        except Exception:
            pass

        try:
            async for chat in self.mongo.Anon.chats.find():
                cid = chat.get("_id") or chat.get("chat_id")
                if isinstance(cid, int):
                    await self.chatsdb.update_one({"_id": cid}, {"$set": {"_id": cid, "title": chat.get("title")}}, upsert=True)
            async for user in self.mongo.Anon.users.find():
                uid = user.get("_id") or user.get("user_id")
                if isinstance(uid, int):
                    await self.usersdb.update_one({"_id": uid}, {"$set": {"_id": uid}}, upsert=True)
        except Exception:
            pass

        await self.cache.update_one({"_id": "migrated"}, {"$set": {"migrated": True}}, upsert=True)
        logger.info("Migration completed successfully.")

    async def crawl_dialogs(self) -> int:
        """Backfill chats collection with every group the userbot assistant is currently in."""
        from pyrogram import enums
        ChatType = enums.ChatType

        count = 0
        crawled_any = False
        for ub in getattr(userbot, "clients", []):
            try:
                async for dialog in ub.get_dialogs():
                    chat = dialog.chat
                    if not chat or not chat.id:
                        continue
                    if chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
                        continue
                    count += 1
                    if not await self.is_chat(chat.id):
                        self.chats.append(chat.id)
                        await self.chatsdb.update_one(
                            {"_id": chat.id},
                            {"$set": {"_id": chat.id, "title": getattr(chat, "title", None)}},
                            upsert=True,
                        )
                crawled_any = True
            except Exception as e:
                logger.warning("Dialog crawl failed for a userbot session: %s", e)
        if crawled_any:
            logger.info("Crawled dialogs: found %d groups.", count)
        return count

    async def load_cache(self) -> None:
        doc = await self.cache.find_one({"_id": "migrated"})
        if not doc:
            await self.migrate_coll()

        await self.get_chats()
        await self.get_users()
        await self.get_blacklisted(True)
        await self.get_logger()
        logger.info(f"Database cache loaded: {len(self.chats)} chats, {len(self.users)} users.")

    async def save_song(self, song_data: dict) -> None:
        """Save downloaded song metadata to database."""
        if not song_data or not song_data.get("id"):
            return
        video_id = song_data["id"]
        try:
            await self.songsdb.update_one(
                {"_id": video_id},
                {"$set": song_data},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Failed to save song to DB: {e}")

    async def get_song(self, video_id: str) -> dict | None:
        """Fetch downloaded song metadata from database."""
        if not video_id:
            return None
        try:
            return await self.songsdb.find_one({"_id": video_id})
        except Exception:
            return None

    async def get_music_cache(self, video_id: str, is_video: bool = False) -> dict | None:
        """Fetch song metadata from shared Telegram Dump cache."""
        try:
            key = f"{video_id}_v" if is_video else f"{video_id}_a"
            doc = await self.music_cachedb.find_one({"_id": key})
            if doc and (doc.get("message_id") or doc.get("file_id")):
                return doc

            # Fallback by video_id
            doc = await self.music_cachedb.find_one({"video_id": video_id})
            if doc and (doc.get("message_id") or doc.get("file_id")):
                return doc

            # Fallback check on shared_song_cache (historical dumped songs)
            shared_doc = await self.storage_db.shared_song_cache.find_one({"_id": key})
            if not shared_doc:
                shared_doc = await self.storage_db.shared_song_cache.find_one({"video_id": video_id})
            if shared_doc and (shared_doc.get("msg_id") or shared_doc.get("message_id")):
                msg_id = shared_doc.get("msg_id") or shared_doc.get("message_id")
                ch_id = shared_doc.get("channel_id") or config.STORAGE_GROUP_ID
                return {
                    "_id": key,
                    "video_id": video_id,
                    "title": shared_doc.get("title") or video_id,
                    "duration": shared_doc.get("duration", 0),
                    "file_id": shared_doc.get("file_id", ""),
                    "message_id": msg_id,
                    "channel_id": ch_id,
                    "is_video": is_video,
                }
        except Exception as e:
            logger.warning(f"get_music_cache failed for {video_id}: {e}")
        return None

    async def save_music_cache(
        self,
        video_id: str,
        title: str,
        duration: int,
        file_path: str,
        message_id: int,
        channel_id: int,
        file_id: str = "",
        is_video: bool = False,
    ) -> None:
        """Save song dump metadata to shared MongoDB."""
        try:
            key = f"{video_id}_v" if is_video else f"{video_id}_a"
            doc = {
                "_id": key,
                "video_id": video_id,
                "title": title,
                "duration": duration,
                "file_path": file_path,
                "file_id": file_id,
                "message_id": message_id,
                "channel_id": channel_id,
                "is_video": is_video,
            }
            await self.music_cachedb.update_one(
                {"_id": key},
                {"$set": doc},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"save_music_cache failed for {video_id}: {e}")

