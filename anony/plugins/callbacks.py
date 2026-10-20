# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import re
import time

from pyrogram import errors, filters, types

from anony import anon, app, db, lang, queue, tg, yt
from anony.helpers import admin_check, buttons, can_manage_vc


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    action, chat_id = args[1], int(args[2])
    qaction = len(args) == 4
    user = query.from_user.mention

    if not await db.get_call(chat_id):
        try:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        except errors.QueryIdInvalid:
            try:
                await query.message.delete()
            except Exception:
                pass
            return

    if action == "status":
        return await query.answer()

    try:
        await query.answer(query.lang["processing"], show_alert=True)
    except errors.QueryIdInvalid:
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        await anon.pause(chat_id)
        if qaction:
            if args[3] == "queued":
                return await query.answer(
                    query.lang["play_paused"].format(user)
                )
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["paused"], False)
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        await anon.resume(chat_id)
        if qaction:
            if args[3] == "queued":
                return await query.answer(
                    query.lang["play_resumed"].format(user)
                )
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["playing"], True)
            )
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await anon.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        m_id = queue.get_current(chat_id).message_id
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except Exception:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        return await anon.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        media.user = user
        await anon.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action == "stop":
        await anon.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    try:
        if action in ["skip", "replay", "stop"]:
            await query.message.reply_text(reply, quote=False)
            await query.message.delete()
        else:
            msg_text = (
                getattr(query.message.caption, "html", None)
                or query.message.caption
                or getattr(query.message.text, "html", None)
                or query.message.text
                or ""
            )
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                msg_text,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(
                chat_id, status=status if action != "resume" else None
            )
        if query.message.caption:
            await query.edit_message_caption(
                caption=f"{mtext}\n\n<blockquote>{reply}</blockquote>",
                reply_markup=keyboard,
            )
        else:
            await query.edit_message_text(
                text=f"{mtext}\n\n<blockquote>{reply}</blockquote>",
                reply_markup=keyboard,
            )
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^queue_(list|back)") & ~app.bl_users)
@lang.language()
async def _queue_callbacks(_, query: types.CallbackQuery):
    data_parts = query.data.split()
    action = data_parts[0].split("_")[1]
    chat_id = int(data_parts[1])

    if not await db.get_call(chat_id):
        return await query.answer(query.lang["not_playing"], show_alert=True)

    _queue = queue.get_queue(chat_id)
    if not _queue:
        return await query.answer(query.lang["not_playing"], show_alert=True)

    _media = _queue[0]
    bot_mention = app.me.mention if hasattr(app, "me") and app.me else "Bot"
    stream_type = "Video" if getattr(_media, "video", False) else "Audio"
    title = f"<a href='{_media.url}'>{_media.title}</a>" if _media.url else _media.title
    user = _media.user or "Unknown"

    if action == "list":
        queue_items = _queue[1:]
        cur_title = f"<a href='{_media.url}'>{_media.title}</a>" if _media.url else _media.title
        cur_duration = _media.duration or "0:00"
        cur_user = _media.user or "Unknown"

        text = (
            "Streaming :\n\n"
            f"✨ Title : {cur_title}\n"
            f"Duration : {cur_duration}\n"
            f"By : {cur_user}\n\n"
            "Queued :"
        )
        if queue_items:
            for item in queue_items[:10]:
                i_title = f"<a href='{item.url}'>{item.title}</a>" if item.url else item.title
                i_duration = item.duration or "0:00"
                i_user = item.user or "Unknown"
                text += (
                    f"\n\n✨ Title : {i_title}\n"
                    f"Duration : {i_duration}\n"
                    f"By : {i_user}"
                )
        else:
            text += "\n\nNo tracks in queue."

        reply_markup = buttons.queue_list_markup(chat_id)
    else:
        text = (
            f"{bot_mention} ᴘʟᴀʏᴇʀ\n\n"
            f"🎄 sᴛʀᴇᴀᴍɪɴɢ : {title}\n\n"
            f"🔗 sᴛʀᴇᴀᴍ ᴛʏᴘᴇ : {stream_type}\n"
            f"🥀 ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ : {user}\n\n"
            f"ᴄʟɪᴄᴋ ᴏɴ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴡʜᴏʟᴇ ǫᴜᴇᴜᴇᴅ ʟɪsᴛ."
        )
        played = _media.time or 0
        duration = _media.duration_sec or 0
        if duration:
            remaining = max(duration - played, 0)
            length = 10
            pos = min(int((played / duration) * length), length - 1)
            bar = "—" * pos + "◉" + "—" * (length - pos - 1)
            slidebar = f"{time.strftime('%M:%S', time.gmtime(played))} | {bar} | -{time.strftime('%M:%S', time.gmtime(remaining))}"
        else:
            slidebar = "00:00 | ◉————————— | -00:00"
        reply_markup = buttons.queue_markup(chat_id, slidebar)

    try:
        if query.message.caption:
            if len(text) > 1020:
                text = text[:1000] + "..."
            await query.edit_message_caption(caption=text, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
    except Exception:
        pass


@app.on_callback_query(filters.regex("help") & ~app.bl_users)
@lang.language()
async def _help(_, query: types.CallbackQuery):
    data = query.data.split()
    if len(data) == 1:
        return await query.answer(url=f"https://t.me/{app.username}?start=help")

    if data[1] == "back":
        return await query.edit_message_text(
            text=query.lang["help_menu"], reply_markup=buttons.help_markup(query.lang)
        )
    elif data[1] == "close":
        try:
            await query.message.delete()
            return await query.message.reply_to_message.delete()
        except Exception:
            return

    await query.edit_message_text(
        text=query.lang[f"help_{data[1]}"],
        reply_markup=buttons.help_markup(query.lang, True),
    )


@app.on_callback_query(filters.regex("settings") & ~app.bl_users)
@lang.language()
@admin_check
async def _settings_cb(_, query: types.CallbackQuery):
    cmd = query.data.split()
    if len(cmd) == 1:
        return await query.answer()
    await query.answer(query.lang.get("processing", "Processing..."), show_alert=False)

    chat_id = query.message.chat.id
    _admin = await db.get_play_mode(chat_id)
    _delete = await db.get_cmd_delete(chat_id)
    _language = await db.get_lang(chat_id)
    _welcome = await db.is_welcome(chat_id)
    _vc_notify = await db.is_vc_notify(chat_id)
    _thumb = await db.is_play_thumb(chat_id)

    action = cmd[1]
    if action == "delete":
        _delete = not _delete
        await db.set_cmd_delete(chat_id, _delete)
    elif action == "play":
        await db.set_play_mode(chat_id, _admin)
        _admin = not _admin
    elif action == "welcome":
        _welcome = not _welcome
        await db.set_welcome(chat_id, _welcome)
    elif action == "vc_notify":
        _vc_notify = not _vc_notify
        await db.set_vc_notify(chat_id, _vc_notify)
    elif action == "thumb":
        _thumb = not _thumb
        await db.set_play_thumb(chat_id, _thumb)

    chat_title = query.message.chat.title or "Chat"
    await query.edit_message_text(
        text=buttons.settings_text(
            chat_title,
            _admin,
            _delete,
            _welcome,
            _vc_notify,
            _thumb,
            _language,
        ),
        reply_markup=buttons.settings_markup(
            query.lang,
            _admin,
            _delete,
            _language,
            chat_id,
            welcome=_welcome,
            vc_notify=_vc_notify,
            play_thumb=_thumb,
        ),
    )


@app.on_callback_query(filters.regex(r"^close$") & ~app.bl_users)
async def _close_callback(_, query: types.CallbackQuery):
    try:
        await query.message.delete()
        if query.message.reply_to_message:
            await query.message.reply_to_message.delete()
    except Exception:
        pass

