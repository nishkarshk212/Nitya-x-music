import asyncio
import html
import os
from pyrogram import enums, filters, types

from anony import app, db, logger
from anony.helpers import buttons, generate_welcome


async def _auto_delete_message(msg: types.Message, delay: int = 3):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
        logger.info(f"Auto-deleted welcome message {msg.id} in chat {msg.chat.id}")
    except Exception as e:
        logger.debug(f"Could not auto-delete welcome message: {e}")


@app.on_message(filters.new_chat_members, group=5)
async def _welcome_member(_, message: types.Message):
    if not message.chat:
        return

    if message.chat.type in (enums.ChatType.SUPERGROUP, enums.ChatType.GROUP):
        asyncio.create_task(db.add_chat(message.chat.id))

    if not await db.is_welcome(message.chat.id):
        return

    logger.info(f"new_chat_members triggered in chat {message.chat.id} ({message.chat.title})")

    for member in message.new_chat_members:
        if member.id == app.id:
            continue

        try:
            logger.info(f"Generating welcome banner for member {member.id} ({member.first_name}) in {message.chat.id}")
            photo = await generate_welcome(app, member, message.chat.id)
            username = f"@{member.username}" if member.username else "-"
            chat_title = html.escape(message.chat.title or "Group")
            text = (
                f"<blockquote><b>𝐖ᴇʟᴄᴏᴍᴇ 𝐓ᴏ {chat_title}\n"
                f"  𝐍ᴀᴍᴇ ✧ {member.mention}\n"
                f"  𝐈ᴅ ✧ {member.id}\n"
                f"  𝐔sᴇʀɴᴀᴍᴇ ✧ {username}</b></blockquote>"
            )
            key = types.InlineKeyboardMarkup(
                [
                    [
                        buttons.ikb(
                            text="add me",
                            url=f"https://t.me/{app.username}?startgroup=true",
                            style=enums.ButtonStyle.SUCCESS,
                        )
                    ]
                ]
            )
            welcome_msg = await message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=key,
            )
            logger.info(f"Welcome message sent to {member.id} in {message.chat.id}. Auto-deleting in 3 seconds...")
            try:
                os.remove(photo)
            except Exception:
                pass

            # Auto-delete welcome message in 3 seconds as requested
            asyncio.create_task(_auto_delete_message(welcome_msg, 3))
        except Exception as e:
            logger.exception(f"Error sending welcome message for member {member.id}: {e}")


@app.on_message(filters.command(["welcome"]) & filters.group & ~app.bl_users)
async def _welcome_cmd(_, message: types.Message):
    if not message.from_user:
        return
    # check admin permissions
    member = await message.chat.get_member(message.from_user.id)
    if member.status not in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
        return await message.reply_text("» Only administrators can configure welcome settings.")

    args = message.text.split()
    chat_id = message.chat.id
    current_status = await db.is_welcome(chat_id)

    if len(args) > 1:
        state = args[1].lower()
        if state in ("on", "enable", "true", "yes"):
            await db.set_welcome(chat_id, True)
            return await message.reply_text("✅ <b>Welcome messages have been enabled.</b>")
        elif state in ("off", "disable", "false", "no"):
            await db.set_welcome(chat_id, False)
            return await message.reply_text("❌ <b>Welcome messages have been disabled.</b>")

    # Toggle or show status
    status_str = "Enabled" if current_status else "Disabled"
    toggle_text = "Disable" if current_status else "Enable"
    buttons_list = [
        [
            types.InlineKeyboardButton(
                text=f"{toggle_text} Welcome",
                callback_data=f"settings welcome",
            )
        ]
    ]
    await message.reply_text(
        f"<b>Welcome Banner Settings:</b>\n\n"
        f"Current status: <b>{status_str}</b>\n\n"
        f"Use <code>/welcome enable</code> or <code>/welcome disable</code>, or click below:",
        reply_markup=types.InlineKeyboardMarkup(buttons_list),
    )

