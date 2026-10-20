# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
from pathlib import Path

from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported, ConnectionError,
                      TransportParseException)
from pyrogram import enums
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import (ChatSendMediaForbidden, ChatSendPhotosForbidden,
                             MessageIdInvalid)
from pyrogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                            InputMediaPhoto, Message)
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from anony import (app, config, db, lang, logger,
                   queue, thumb, userbot, yt)
from anony.helpers import Media, Track, buttons


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        self._dl_queue = asyncio.Queue()
        self._dl_tasks = []
        self._downloading = set()
        self.last_track = {}
        self.played_tracks = {}
        self.autoplay_active = {}
        self.empty_prompt_msg = {}
        self._vc_join_cooldown = {}
        self.group_call_chats = {}

    async def _dl_worker(self):
        while True:
            media = await self._dl_queue.get()
            try:
                if media and not getattr(media, "file_path", None):
                    await self.download_track(media)
            except Exception as e:
                logger.warning(f"Background download error: {e}")
            finally:
                self._dl_queue.task_done()

    def queue_download(self, media: Track | Media) -> None:
        """Enqueue track for background download so it is ready in 0 ms."""
        if not media or getattr(media, "file_path", None):
            return
        if getattr(media, "id", None) in self._downloading:
            return
        self._downloading.add(media.id)
        self._dl_queue.put_nowait(media)

    async def download_track(self, media: Track | Media) -> str | None:
        """Download track in background, pre-generate thumbnail, and cache metadata."""
        if not media:
            return None
        if getattr(media, "file_path", None) and Path(media.file_path).exists():
            return media.file_path

        video = getattr(media, "video", False)
        for ext_cand in (["mp4"] if video else ["mp3", "webm", "m4a", "opus", "mp4"]):
            fname = f"downloads/{media.id}.{ext_cand}"
            if Path(fname).exists() and Path(fname).stat().st_size > 1024:
                media.file_path = fname
                if hasattr(media, "title") and media.title:
                    yt.save_track_meta(media)
                    await db.save_song({
                        "id": media.id,
                        "title": media.title,
                        "duration": getattr(media, "duration", "0:00"),
                        "duration_sec": getattr(media, "duration_sec", 0),
                        "file_path": fname,
                        "video": video,
                    })
                return fname

        try:
            file_path = await yt.download(
                media.id,
                video=video,
                title=getattr(media, "title", ""),
                duration=getattr(media, "duration_sec", 0),
            )
            if file_path:
                media.file_path = file_path
                yt.save_track_meta(media)
                if config.THUMB_GEN and isinstance(media, Track):
                    try:
                        await thumb.generate(media)
                    except Exception:
                        pass
                if hasattr(media, "title") and media.title:
                    await db.save_song({
                        "id": media.id,
                        "title": media.title,
                        "duration": getattr(media, "duration", "0:00"),
                        "duration_sec": getattr(media, "duration_sec", 0),
                        "file_path": file_path,
                        "video": video,
                    })
                return file_path
        except Exception as e:
            logger.warning(f"Download failed for {media.id}: {e}")
        finally:
            self._downloading.discard(media.id)
        return None

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        try:
            return await client.pause(chat_id)
        except (ConnectionNotFound, exceptions.NotInCallError):
            await self.stop(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        try:
            return await client.resume(chat_id)
        except (ConnectionNotFound, exceptions.NotInCallError):
            await self.stop(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)
        self.last_track.pop(chat_id, None)
        self.played_tracks.pop(chat_id, None)
        self.autoplay_active.pop(chat_id, None)
        if prompt_id := self.empty_prompt_msg.pop(chat_id, None):
            try:
                await app.delete_messages(chat_id=chat_id, message_ids=prompt_id)
            except Exception:
                pass

        try:
            await client.leave_call(chat_id, close=False)
        except Exception:
            pass


    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media)
            if isinstance(media, (Track, Media))
            else None
        ) if config.THUMB_GEN else None
        _thumb = _thumb or config.DEFAULT_THUMB
        if not await db.is_play_thumb(chat_id):
            _thumb = None

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if media.video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                self.last_track[chat_id] = media
                if getattr(media, "id", None):
                    if chat_id not in self.played_tracks:
                        self.played_tracks[chat_id] = []
                    if media.id not in self.played_tracks[chat_id]:
                        self.played_tracks[chat_id].append(media.id)
                    if len(self.played_tracks[chat_id]) > 50:
                        self.played_tracks[chat_id].pop(0)
                title = f"<a href='{media.url}'>{media.title}</a>" if media.url else media.title
                dur = media.duration or (
                    f"{media.duration_sec // 60}:{media.duration_sec % 60:02d}"
                    if getattr(media, "duration_sec", 0)
                    else "0:00"
                )
                text = (
                    f"<blockquote>Sᴏᴜɴᴅ Ɛɴɢᴀɢᴇᴅ ┊ {dur}  ◤</blockquote>\n"
                    f"<blockquote>𝖳ɪᴛʟᴇ : {title}\n"
                    f"𝖯ʟᴀʏᴇᴅ 𝖡ʏ : {media.user}</blockquote>"
                )
                keyboard = buttons.controls(chat_id)
                try:
                    if _thumb:
                        await message.edit_media(
                            media=InputMediaPhoto(
                                media=_thumb,
                                caption=text,
                                has_spoiler=True,
                            ),
                            reply_markup=keyboard,
                        )
                    else:
                        await message.edit_text(text, reply_markup=keyboard)
                except (ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid):
                    if _thumb:
                        sent = await app.send_photo(
                            chat_id=chat_id,
                            photo=_thumb,
                            caption=text,
                            reply_markup=keyboard,
                            has_spoiler=True,
                        )
                    else:
                        sent = await app.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=keyboard,
                        )
                    media.message_id = sent.id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            video_id = getattr(media, "id", "?")
            logger.warning(f"NoAudioSourceFound for {video_id} (path: {media.file_path}). Initiating auto-recovery...")
            recovered = False

            # 1. Attempt fast ffmpeg audio transcode if file exists locally
            if media.file_path and Path(media.file_path).exists():
                fixed_path = f"downloads/{video_id}_fixed.mp3"
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "ffmpeg", "-y", "-i", str(Path(media.file_path).resolve()),
                        "-vn", "-acodec", "libmp3lame", "-ar", "48000", "-ac", "2", fixed_path,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await asyncio.wait_for(proc.communicate(), timeout=20)
                    if Path(fixed_path).exists() and Path(fixed_path).stat().st_size > 1024:
                        import shutil
                        shutil.move(fixed_path, media.file_path)
                        stream = types.MediaStream(
                            media_path=str(Path(media.file_path).resolve()),
                            audio_parameters=types.AudioQuality.HIGH,
                            video_parameters=types.VideoQuality.HD_720p,
                            audio_flags=types.MediaStream.Flags.REQUIRED,
                            video_flags=types.MediaStream.Flags.IGNORE,
                            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
                        )
                        await client.play(
                            chat_id=chat_id,
                            stream=stream,
                            config=types.GroupCallConfig(auto_start=False),
                        )
                        recovered = True
                        logger.info(f"Successfully auto-recovered playback for {video_id} via ffmpeg transcode!")
                except Exception as fix_err:
                    logger.warning(f"Audio transcode recovery failed for {video_id}: {fix_err}")
                    if Path(fixed_path).exists():
                        Path(fixed_path).unlink(missing_ok=True)

            # 2. If transcode failed, purge the corrupt cached file and trigger a fresh download
            if not recovered:
                try:
                    if media.file_path and Path(media.file_path).exists():
                        Path(media.file_path).unlink(missing_ok=True)
                    # Also purge corrupt file from /var/music_storage
                    for c_ext in ["mp3", "webm", "m4a", "opus", "mp4"]:
                        vps_p = Path(f"/var/music_storage/{video_id}.{c_ext}")
                        if vps_p.exists():
                            vps_p.unlink(missing_ok=True)

                    media.file_path = None
                    dl_path = await yt._download_via_ytdlp(video_id, video=media.video)
                    if dl_path and Path(dl_path).exists() and Path(dl_path).stat().st_size > 1024:
                        media.file_path = dl_path
                        stream = types.MediaStream(
                            media_path=str(Path(dl_path).resolve()),
                            audio_parameters=types.AudioQuality.HIGH,
                            video_parameters=types.VideoQuality.HD_720p,
                            audio_flags=types.MediaStream.Flags.REQUIRED,
                            video_flags=(
                                types.MediaStream.Flags.AUTO_DETECT
                                if media.video
                                else types.MediaStream.Flags.IGNORE
                            ),
                            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
                        )
                        await client.play(
                            chat_id=chat_id,
                            stream=stream,
                            config=types.GroupCallConfig(auto_start=False),
                        )
                        recovered = True
                        logger.info(f"Successfully recovered playback for {video_id} via clean re-download!")
                except Exception as dl_err:
                    logger.warning(f"Re-download recovery failed for {video_id}: {dl_err}")

            if not recovered:
                await message.edit_text(_lang["error_no_audio"])
                await self.play_next(chat_id)
        except (ConnectionError, ConnectionNotFound, TelegramServerError,
                TransportParseException, TimeoutError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])


    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        media = queue.get_current(chat_id)
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)


    async def play_next(self, chat_id: int) -> None:
        if loop := await db.get_loop(chat_id):
            await db.set_loop(chat_id, loop - 1)
            return await self.replay(chat_id)

        media = queue.get_next(chat_id)
        if not media:
            if self.autoplay_active.get(chat_id):
                if await self.handle_autoplay(chat_id):
                    return
            return await self.send_queue_empty(chat_id)

        try:
            if media.message_id:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except Exception:
            pass

        # Check if already downloaded on disk
        if not media.file_path or not Path(media.file_path).exists():
            for ext_cand in (["mp4"] if getattr(media, "video", False) else ["mp3", "webm", "m4a", "opus", "mp4"]):
                fname = f"downloads/{media.id}.{ext_cand}"
                if Path(fname).exists() and Path(fname).stat().st_size > 1024:
                    media.file_path = fname
                    break

        # Proactively queue background download for the next upcoming track in line
        upcoming = queue.get_next(chat_id, check=True)
        if upcoming and not upcoming.file_path:
            self.queue_download(upcoming)

        _lang = await lang.get_lang(chat_id)

        if media.file_path and Path(media.file_path).exists():
            # 0 ms INSTANT PLAY: play directly from local disk
            sent = await app.send_message(chat_id=chat_id, text=_lang["processing"])
            media.message_id = sent.id
            await self.play_media(chat_id, sent, media)
        else:
            # Download locally first (~0.8s from VPS) to guarantee 100% full, uninterrupted playback
            msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
            media.file_path = await self.download_track(media)
            if not media.file_path:
                await self.play_next(chat_id)
                return await msg.edit_text(
                    _lang["error_no_file"].format(config.SUPPORT_CHAT)
                )
            media.message_id = msg.id
            await self.play_media(chat_id, msg, media)


    async def send_queue_empty(self, chat_id: int) -> None:
        last_media = self.last_track.get(chat_id)
        if last_media and getattr(last_media, "message_id", None):
            try:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=last_media.message_id,
                    revoke=True,
                )
                last_media.message_id = 0
            except Exception:
                pass

        # Disconnect assistant from voice chat automatically when playlist ends
        client = await db.get_assistant(chat_id)
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)
        self.autoplay_active.pop(chat_id, None)
        try:
            await client.leave_call(chat_id, close=False)
        except Exception:
            pass

        _lang = await lang.get_lang(chat_id)
        text = _lang.get(
            "autoplay_queue_empty",
            (
                "<blockquote><b>𝖭ᴏ 𝖬ᴏʀᴇ 𝖲ᴏɴɢs ɪɴ ᴛʜᴇ 𝖰ᴜᴇᴜᴇ\n"
                "ᴛʜᴇ ᴘʟᴀʏʟɪsᴛ ʜᴀs ᴇɴᴅᴇᴅ — ʜɪᴛ ᴀᴜᴛᴏᴘʟᴀʏ ᴛᴏ ᴋᴇᴇᴘ ᴛʜᴇ ᴍᴜsɪᴄ ɢᴏɪɴɢ.</b></blockquote>"
            ),
        )
        keyboard = buttons.autoplay_prompt_markup(chat_id)
        try:
            sent = await app.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
            )
            self.empty_prompt_msg[chat_id] = sent.id
        except Exception as e:
            logger.warning(f"Failed to send queue empty message: {e}")


    async def handle_autoplay(self, chat_id: int, force: bool = False) -> bool:
        if not force and not await db.is_autoplay(chat_id):
            return False

        last_media = self.last_track.get(chat_id)
        if not last_media or not getattr(last_media, "id", None):
            return False

        _lang = await lang.get_lang(chat_id)
        video_id = last_media.id
        title = getattr(last_media, "title", "")
        video = getattr(last_media, "video", False)

        candidates = await yt.get_related(video_id=video_id, title=title, video=video)
        if not candidates:
            return False

        played = set(self.played_tracks.get(chat_id, []))
        chosen = None
        for cand in candidates:
            if cand.id not in played:
                chosen = cand
                break

        if not chosen:
            for cand in candidates:
                if cand.id != video_id:
                    chosen = cand
                    break
            if not chosen:
                chosen = candidates[0]

        chosen.user = "˹ᴧᴜᴛᴏᴘʟᴧʏ˼ 📻"
        chosen.video = video

        queue.add(chat_id, chosen)
        if chat_id not in self.played_tracks:
            self.played_tracks[chat_id] = []
        if chosen.id not in self.played_tracks[chat_id]:
            self.played_tracks[chat_id].append(chosen.id)

        for ext_cand in (["mp4"] if video else ["mp3", "webm", "m4a", "opus", "mp4"]):
            fname = f"downloads/{chosen.id}.{ext_cand}"
            if Path(fname).exists() and Path(fname).stat().st_size > 1024:
                chosen.file_path = fname
                break

        # Proactively queue background download for the next recommendation
        for next_cand in candidates:
            if next_cand.id != chosen.id and next_cand.id not in played:
                self.queue_download(next_cand)
                break

        # Delete previous track message or empty prompt if present
        if last_media and getattr(last_media, "message_id", None):
            try:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=last_media.message_id,
                    revoke=True,
                )
            except Exception:
                pass

        if prompt_id := self.empty_prompt_msg.pop(chat_id, None):
            try:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=prompt_id,
                    revoke=True,
                )
            except Exception:
                pass

        self.autoplay_active[chat_id] = True

        if chosen.file_path:
            sent = await app.send_message(chat_id=chat_id, text=_lang["processing"])
            chosen.message_id = sent.id
            await self.play_media(chat_id, sent, chosen)
        else:
            stream_url = await yt.get_stream_url(chosen.id, video=video)
            if stream_url:
                chosen.file_path = stream_url
                self.queue_download(chosen)
                sent = await app.send_message(chat_id=chat_id, text=_lang["processing"])
                chosen.message_id = sent.id
                await self.play_media(chat_id, sent, chosen)
            else:
                msg = await app.send_message(chat_id=chat_id, text=_lang["processing"])
                chosen.file_path = await self.download_track(chosen)
                if not chosen.file_path:
                    queue.remove_current(chat_id)
                    return await self.handle_autoplay(chat_id, force=force)
                chosen.message_id = msg.id
                await self.play_media(chat_id, msg, chosen)

        return True


    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 3) if pings else 0.0

    async def notify_vc_join(self, chat_id: int, user_id: int) -> None:
        try:
            if not await db.is_vc_notify(chat_id):
                return

            ub_ids = [u.me.id for u in userbot.clients if getattr(u, "me", None)]
            bot_id = getattr(app.me, "id", None) if getattr(app, "me", None) else None
            if user_id in ub_ids or user_id == bot_id or user_id <= 0:
                return

            import time
            now = time.time()
            if chat_id not in self._vc_join_cooldown:
                self._vc_join_cooldown[chat_id] = {}

            if now - self._vc_join_cooldown[chat_id].get(user_id, 0) < 15:
                return
            self._vc_join_cooldown[chat_id][user_id] = now

            user = None
            try:
                user = await app.get_users(user_id)
            except Exception:
                pass

            if user:
                user_name = user.first_name or "User"
                mention = f"<a href='tg://user?id={user.id}'>{user_name}</a>"
            else:
                mention = f"<a href='tg://user?id={user_id}'>User</a>"

            # Check AUTH role (Owner / Admin / Member)
            role = "Member"
            try:
                if user_id in app.sudoers:
                    role = "Owner"
                else:
                    member = await app.get_chat_member(chat_id, user_id)
                    if member.status == ChatMemberStatus.OWNER:
                        role = "Owner"
                    elif member.status == ChatMemberStatus.ADMINISTRATOR:
                        role = "Admin"
                    elif await db.is_auth(chat_id, user_id):
                        role = "Admin"
            except Exception:
                try:
                    admins = await db.get_admins(chat_id)
                    if user_id in admins:
                        role = "Admin"
                except Exception:
                    pass

            text = (
                f"<blockquote><b>#JoinedVc\n"
                f"ⓘ User - {mention}\n"
                f"ⓘ UserID - <code>{user_id}</code>\n"
                f"ⓘ AUTH - {role}</b></blockquote>"
            )

            chat = None
            try:
                chat = await app.get_chat(chat_id)
            except Exception:
                pass

            if chat and getattr(chat, "username", None):
                vc_url = f"https://t.me/{chat.username}?videochat"
            else:
                c_id = str(chat_id).replace("-100", "").replace("-", "")
                vc_url = f"https://t.me/c/{c_id}?videochat"

            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="💫 JOIN VC", url=vc_url, style=enums.ButtonStyle.SUCCESS)]]
            )

            sent_msg = await app.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            if sent_msg:
                async def _auto_del_vc_msg(msg):
                    await asyncio.sleep(5)
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                asyncio.create_task(_auto_del_vc_msg(sent_msg))
        except Exception as e:
            err_str = str(e)
            if "CHANNEL_INVALID" not in err_str and "CHAT_WRITE_FORBIDDEN" not in err_str:
                logger.warning(f"Error sending VC join notification in {chat_id}: {e}")

    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)
            elif isinstance(update, types.UpdatedGroupCallParticipant):
                if update.action == types.GroupCallParticipant.Action.JOINED:
                    user_id = getattr(update.participant, "user_id", None)
                    if user_id:
                        asyncio.create_task(self.notify_vc_join(update.chat_id, user_id))

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)

            @ub.on_raw_update()
            async def raw_vc_handler(c, update, users, chats):
                from pyrogram.raw.types import (
                    UpdateGroupCall,
                    UpdateGroupCallParticipants,
                    PeerChannel,
                    PeerChat,
                    PeerUser,
                )
                try:
                    if isinstance(update, UpdateGroupCall):
                        cid = None
                        if isinstance(update.peer, PeerChannel):
                            cid = int(f"-100{update.peer.channel_id}")
                        elif isinstance(update.peer, PeerChat):
                            cid = int(f"-{update.peer.chat_id}")
                        if cid and hasattr(update, "call") and hasattr(update.call, "id"):
                            self.group_call_chats[update.call.id] = cid

                    elif isinstance(update, UpdateGroupCallParticipants):
                        call_id = getattr(update.call, "id", None)
                        chat_id = self.group_call_chats.get(call_id)
                        if not chat_id:
                            return
                        for p in getattr(update, "participants", []):
                            if getattr(p, "just_joined", False) or (
                                not getattr(p, "left", False)
                                and getattr(p, "active_date", 0) > 0
                            ):
                                uid = None
                                if isinstance(getattr(p, "peer", None), PeerUser):
                                    uid = p.peer.user_id
                                if uid:
                                    asyncio.create_task(self.notify_vc_join(chat_id, uid))
                except Exception:
                    pass

        for _ in range(2):
            self._dl_tasks.append(asyncio.create_task(self._dl_worker()))
        logger.info("PyTgCalls client(s) started.")
