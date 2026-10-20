# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import time
import asyncio

from pyrogram import enums, errors, filters, types

from anony import anon, app, config, db, lang, logger, queue, tasks, userbot, yt
from anony.helpers import buttons


def format_duration(seconds: int) -> str:
    if not seconds:
        return "0s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}m" if minutes == 0 else f"{hours}h {minutes}m")
    elif minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


@app.on_message(filters.video_chat_started, group=19)
async def _vc_started(_, m: types.Message):
    try:
        if m.from_user:
            user_name = m.from_user.first_name or "User"
            started_by = f"<a href='tg://user?id={m.from_user.id}'>{user_name}</a>"
            id_val = m.from_user.id
        elif m.sender_chat:
            started_by = m.sender_chat.title or "Chat"
            id_val = m.sender_chat.id
        else:
            started_by = m.chat.title or "Chat"
            id_val = m.chat.id

        text = (
            f"<blockquote><b>ᴠɪᴅᴇᴏ ᴄʜᴀᴛ sᴛᴀʀᴛᴇᴅ\n"
            f"──────────\n"
            f"sᴛᴀʀᴛᴇᴅ ʙʏ: {started_by}\n"
            f"ɪᴅ: <code>{id_val}</code>\n"
            f"──────────</b></blockquote>"
        )

        if m.chat.username:
            vc_url = f"https://t.me/{m.chat.username}?videochat"
        else:
            c_id = str(m.chat.id).replace("-100", "").replace("-", "")
            vc_url = f"https://t.me/c/{c_id}?videochat"

        markup = types.InlineKeyboardMarkup(
            [[types.InlineKeyboardButton(text="💫 JOIN VC", url=vc_url, style=enums.ButtonStyle.SUCCESS)]]
        )

        await m.reply_text(text, reply_markup=markup, disable_web_page_preview=True)
    except Exception as e:
        logger.warning(f"Error handling video_chat_started in {m.chat.id}: {e}")


@app.on_message(filters.video_chat_ended, group=20)
async def _vc_ended(_, m: types.Message):
    await anon.stop(m.chat.id)
    try:
        if m.from_user:
            user_name = m.from_user.first_name or "User"
            ended_by = f"<a href='tg://user?id={m.from_user.id}'>{user_name}</a>"
            id_val = m.from_user.id
        elif m.sender_chat:
            ended_by = m.sender_chat.title or "Chat"
            id_val = m.sender_chat.id
        else:
            ended_by = m.chat.title or "Chat"
            id_val = m.chat.id

        duration_sec = getattr(m.video_chat_ended, "duration", 0)
        duration_str = format_duration(duration_sec)

        text = (
            f"<blockquote><b>ᴠɪᴅᴇᴏ ᴄʜᴀᴛ ᴇɴᴅᴇᴅ\n"
            f"──────────\n"
            f"ᴇɴᴅᴇᴅ ʙʏ: {ended_by}\n"
            f"ɪᴅ: <code>{id_val}</code>\n"
            f"ᴅᴜʀᴀᴛɪᴏɴ: {duration_str}\n"
            f"──────────</b></blockquote>"
        )
        await m.reply_text(text, disable_web_page_preview=True)
    except Exception as e:
        logger.warning(f"Error handling video_chat_ended in {m.chat.id}: {e}")


async def auto_leave():
    while True:
        await asyncio.sleep(3600)
        for ub in userbot.clients:
            try:
                chats = [dialog.chat.id async for dialog in ub.get_dialogs()
                            if dialog.chat.type in [
                                enums.ChatType.GROUP, enums.ChatType.SUPERGROUP,
                            ]][-20:]
                for chat in chats:
                    if chat in [app.logger, -1001686672798, -1001549206010]:
                        continue
                    if chat in db.active_calls:
                        continue
                    await ub.leave_chat(chat)
                    await asyncio.sleep(12)
            except asyncio.CancelledError:
                raise
            except Exception:
                continue


async def track_time():
    try:
        while True:
            await asyncio.sleep(1)
            for chat_id in list(db.active_calls):
                if not await db.playing(chat_id):
                    continue

                media = queue.get_current(chat_id)
                if not media:
                    continue
                media.time += 1
    except asyncio.CancelledError:
        raise


async def update_timer(length=10, sleep=12):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            try:
                media = queue.get_current(chat_id)
                if not media:
                    continue
                duration, message_id = media.duration_sec, media.message_id
                if not duration or not message_id or not media.time:
                    continue
                played = media.time
                remaining = max(duration - played, 0)
                pos = min(int((played / duration) * length), length - 1)
                timer = "—" * pos + "◉" + "—" * (length - pos - 1)

                if remaining <= 30:
                    next = queue.get_next(chat_id, check=True)
                    if next and not next.file_path:
                        anon.queue_download(next)

                if remaining < 10:
                    remove = True
                else:
                    if config.THUMB_GEN:
                        timer = f"{time.strftime('%M:%S', time.gmtime(played))} | {timer} | -{time.strftime('%M:%S', time.gmtime(remaining))}"
                    else:
                        timer = None
                    remove = False

                if not timer and not remove:
                    continue

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id, timer=timer, remove=remove
                    ),
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                pass


async def vc_watcher(sleep=15):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            try:
                client = await db.get_assistant(chat_id)
                media = queue.get_current(chat_id)
                if not media:
                    await anon.stop(chat_id)
                    continue
                participants = await client.get_participants(chat_id)
                if len(participants) < 2 and getattr(media, "time", 0) > 30:
                    _lang = await lang.get_lang(chat_id)
                    try:
                        sent = await app.edit_message_reply_markup(
                            chat_id=chat_id,
                            message_id=media.message_id,
                            reply_markup=buttons.controls(
                                chat_id=chat_id, status=_lang["stopped"], remove=True
                            ),
                        )
                        await anon.stop(chat_id)
                        await sent.reply_text(_lang["auto_left"])
                    except Exception:
                        await anon.stop(chat_id)
            except Exception:
                pass


if config.AUTO_END:
    tasks.append(asyncio.create_task(vc_watcher()))
if config.AUTO_LEAVE:
    tasks.append(asyncio.create_task(auto_leave()))
tasks.append(asyncio.create_task(track_time()))
tasks.append(asyncio.create_task(update_timer()))
