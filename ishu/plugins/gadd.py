# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio

from pyrogram import enums, filters, types

from ishu import app, config, db


@app.on_message(filters.command("gadd") & filters.user(config.OWNER_ID))
async def add_allbot(_, message: types.Message):
    if len(message.command) < 2:
        return await message.reply(
            "❍ ɪɴᴠᴀʟɪᴅ ᴄᴏᴍᴍᴀɴᴅ ғᴏʀᴍᴀᴛ. ᴘʟᴇᴀsᴇ ᴜsᴇ ʟɪᴋᴇ » <code>/gadd Bot_username</code>"
        )

    bot_username = message.command[1]
    try:
        bot = await app.get_users(bot_username)
    except Exception:
        return await message.reply(f"❍ ᴄᴏᴜʟᴅ ɴᴏᴛ ғɪɴᴅ ᴜsᴇʀ: {bot_username}")

    # The userbot (assistant) that manages this chat — only assistants can
    # add members, so route through db.get_client, which returns the Client.
    userbot_client = await db.get_client(message.chat.id)
    ub_name = getattr(userbot_client, "username", None) or "userbot"

    status = await message.reply("❍ ᴀᴅᴅɪɴɢ ɢɪᴠᴇɴ ʙᴏᴛ ɪɴ ᴀʟʟ ᴄʜᴀᴛs!")
    done = 0
    failed = 0
    added_groups = []

    # NOTE: get_dialogs() is the working iterator in this framework (bots
    # can't call GetDialogs directly, and get_chats() is the raw-API wrapper
    # that returns a single Dialogs object, not an async iterator). The
    # crawl_dialogs() helper in mongo.py uses exactly this pattern.
    async for dialog in userbot_client.get_dialogs():
        chat = dialog.chat
        if chat.type not in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
            continue
        try:
            await userbot_client.add_chat_members(chat.id, bot.id)
            done += 1
            added_groups.append(f"• {chat.title} (<code>{chat.id}</code>)")
        except Exception:
            failed += 1

        if (done + failed) % 5 == 0:
            try:
                await status.edit(
                    f"❍ ᴀᴅᴅɪɴɢ {bot_username}\n\n"
                    f"➥ ᴀᴅᴅᴇᴅ ɪɴ {done} ᴄʜᴀᴛs ✔\n"
                    f"➥ ғᴀɪʟᴇᴅ ɪɴ {failed} ᴄʜᴀᴛs ✘\n\n"
                    f"➲ ᴀᴅᴅᴇᴅ ʙʏ » @{ub_name}"
                )
            except Exception:
                pass
        await asyncio.sleep(3)

    await status.edit(
        f"❍ {bot_username} ʙᴏᴛ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ 🎉\n\n"
        f"➥ ᴀᴅᴅᴇᴅ ɪɴ {done} ᴄʜᴀᴛs ✅\n"
        f"➥ ғᴀɪʟᴇᴅ ɪɴ {failed} ᴄʜᴀᴛs ✘\n\n"
        f"➲ ᴀᴅᴅᴇᴅ ʙʏ » @{ub_name}"
    )

    if added_groups:
        # Send group list in chunks to avoid message length limit
        chunk_size = 50
        for i in range(0, len(added_groups), chunk_size):
            chunk = added_groups[i : i + chunk_size]
            header = (
                f"❍ <b>ɢʀᴏᴜᴘs ᴡʜᴇʀᴇ {bot_username} ᴡᴀs ᴀᴅᴅᴇᴅ</b>"
                f" ({i + 1}–{i + len(chunk)}/{len(added_groups)}):\n\n"
            )
            await message.reply(header + "\n".join(chunk))
