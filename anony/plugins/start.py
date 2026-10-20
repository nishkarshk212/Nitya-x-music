# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
import time
from pyrogram import enums, filters, types

from anony import app, boot, config, db, lang
from anony.helpers import buttons, utils


@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    await m.reply_text(
        text=m.lang["help_menu"],
        reply_markup=buttons.help_markup(m.lang),
        quote=True,
    )


@app.on_message(filters.command(["help"]) & filters.group & ~app.bl_users)
async def _help_group(_, m: types.Message):
    await m.reply_text(
        text="<b>ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴍʏ ʜᴇʟᴘ ᴍᴇɴᴜ ɪɴ ʏᴏᴜʀ ᴘᴍ.</b>",
        reply_markup=buttons.help_group_key("Help"),
        quote=True,
    )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    try:
        import random
        emojis = ["⚡", "🔥", "✨", "❤️", "🎉", "🕊️"]
        await message.react(random.choice(emojis))
    except Exception:
        pass

    anim_frames = [
        "<blockquote><b>⟡ Sᴛᴀʀᴛɪɴɢ Nɪᴛʏᴀ Mᴜsɪᴄ...</b></blockquote>",
        "<blockquote><b>⟡ Lᴏᴀᴅɪɴɢ Cᴏʀᴇ Mᴏᴅᴜʟᴇs... ⚙️</b></blockquote>",
        "<blockquote><b>⟡ Cᴏɴɴᴇᴄᴛɪɴɢ Sᴇʀᴠᴇʀs... ⚡</b></blockquote>",
        "<blockquote><b>⟡ Iɴɪᴛɪᴀʟɪᴢᴀᴛɪᴏɴ Cᴏᴍᴘʟᴇᴛᴇ! ✨</b></blockquote>",
    ]
    anim_msg = None
    try:
        anim_msg = await message.reply_text(anim_frames[0], quote=True)
        for frame in anim_frames[1:]:
            await asyncio.sleep(0.35)
            await anim_msg.edit_text(frame)
        await asyncio.sleep(0.3)
    except Exception:
        pass

    private = message.chat.type == enums.ChatType.PRIVATE
    bot_mention = app.mention

    if private:
        user_mention = (
            message.from_user.mention
            if message.from_user
            else (message.author_signature or message.chat.title or "User")
        )
        owner_mention = getattr(app, "owner_mention", None)
        if not owner_mention or "tg://user" in owner_mention:
            try:
                owner = await app.get_users(config.OWNER_ID)
                owner_mention = owner.mention
                app.owner_mention = owner_mention
            except Exception:
                owner_mention = f"<a href='tg://user?id={config.OWNER_ID}'>Owner</a>"

        _text = (
            f"<b>╭───────────────────▣\n"
            f"│❍ ʜᴇʏ {user_mention}•\n"
            f"│❍ ɪ ᴀᴍ {bot_mention} ♪ •\n"
            f"├───────────────────▣\n"
            f"│❍ ʙᴇsᴛ ǫᴜɪʟɪᴛʏ ғᴇᴀᴛᴜʀᴇs •\n"
            f"│❍ ᴍᴀᴅᴇ ʙʏ...{owner_mention} •\n"
            f"╰───────────────────▣</b>"
        )
    else:
        uptime_sec = int(time.time() - boot)
        days = uptime_sec // 86400
        hours = (uptime_sec // 3600) % 24
        minutes = (uptime_sec // 60) % 60
        seconds = uptime_sec % 60
        uptime = (
            f"{days}ᴅ:{hours}ʜ:{minutes}ᴍ:{seconds}s"
            if days > 0
            else f"{hours}ʜ:{minutes}ᴍ:{seconds}s"
        )
        _text = (
            f"<b>{bot_mention}♪ ɪs ᴀʟɪᴠᴇ ʙᴀʙʏ.\n\n"
            f"✫ ᴜᴘᴛɪᴍᴇ : {uptime}</b>"
        )

    key = buttons.start_key(message.lang, private)
    await message.reply_photo(
        photo=config.START_IMG,
        caption=_text,
        reply_markup=key,
        has_spoiler=True,
        quote=not private,
    )
    if anim_msg:
        try:
            await anim_msg.delete()
        except Exception:
            pass

    if private:
        if await db.is_user(message.from_user.id):
            return
        await utils.send_log(message)
        await db.add_user(message.from_user.id)
    else:
        if await db.is_chat(message.chat.id):
            return
        await utils.send_log(message, True)
        await db.add_chat(message.chat.id)


@app.on_message(filters.command(["playmode", "settings", "setting", "cplaymode", "csettings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    admin_only = await db.get_play_mode(message.chat.id)
    cmd_delete = await db.get_cmd_delete(message.chat.id)
    _language = await db.get_lang(message.chat.id)
    _welcome = await db.is_welcome(message.chat.id)
    _vc_notify = await db.is_vc_notify(message.chat.id)
    _thumb = await db.is_play_thumb(message.chat.id)
    chat_title = message.chat.title or "Chat"
    await message.reply_text(
        text=buttons.settings_text(
            chat_title,
            admin_only,
            cmd_delete,
            _welcome,
            _vc_notify,
            _thumb,
            _language,
        ),
        reply_markup=buttons.settings_markup(
            message.lang,
            admin_only,
            cmd_delete,
            _language,
            message.chat.id,
            welcome=_welcome,
            vc_notify=_vc_notify,
            play_thumb=_thumb,
        ),
        quote=True,
    )


@app.on_message(filters.command(["playmode", "settings", "setting", "cplaymode", "csettings"]) & filters.private & ~app.bl_users)
async def settings_pm(_, message: types.Message):
    await message.reply_text(
        "<blockquote><b>⚙️ The <code>/settings</code> command is meant for Groups.\n\n"
        "Add me to your group and send <code>/settings</code> there to configure Welcome messages, VC Join alerts, Thumbnails, and Play mode!</b></blockquote>"
    )


@app.on_message(filters.new_chat_members, group=7)
@lang.language()
async def _new_member(_, message: types.Message):
    if message.chat.type != enums.ChatType.SUPERGROUP:
        return await message.chat.leave()

    await asyncio.sleep(3)
    for member in message.new_chat_members:
        if member.id == app.id:
            if await db.is_chat(message.chat.id):
                return
            await utils.send_log(message, True)
            await db.add_chat(message.chat.id)
