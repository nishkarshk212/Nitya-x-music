# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllPrivateChats,
)
import logging

logger = logging.getLogger("anony")


# Group chat commands for members
GROUP_COMMANDS = [
    BotCommand("play", "Play requested audio track in voice chat"),
    BotCommand("vplay", "Play requested video in voice chat"),
    BotCommand("pause", "Pause currently playing stream"),
    BotCommand("resume", "Resume paused stream"),
    BotCommand("skip", "Skip to next track in queue"),
    BotCommand("stop", "Stop stream and clear queue"),
    BotCommand("queue", "View queue and current playing song"),
    BotCommand("seek", "Seek stream forward (e.g. /seek 20)"),
    BotCommand("seekback", "Seek stream backward (e.g. /seekback 20)"),
    BotCommand("loop", "Loop current stream (e.g. /loop 3)"),
    BotCommand("autoplay", "Toggle autoplay recommended tracks"),
    BotCommand("settings", "Open chat music settings"),
    BotCommand("welcome", "Enable/disable welcome banner"),
    BotCommand("vcnotify", "Enable/disable VC join notifications"),
    BotCommand("authlist", "List authorized users in group"),
    BotCommand("ping", "Check bot latency and uptime"),
    BotCommand("stats", "View bot and system statistics"),
    BotCommand("language", "Change chat language"),
    BotCommand("vps", "Check server disk and storage usage"),
    BotCommand("help", "Show help menu and command guide"),
]

# Admin commands for group administrators
ADMIN_COMMANDS = [
    BotCommand("play", "Play requested audio track in voice chat"),
    BotCommand("vplay", "Play requested video in voice chat"),
    BotCommand("pause", "Pause currently playing stream"),
    BotCommand("resume", "Resume paused stream"),
    BotCommand("skip", "Skip to next track in queue"),
    BotCommand("stop", "Stop stream and clear queue"),
    BotCommand("queue", "View queue and current playing song"),
    BotCommand("seek", "Seek stream forward (e.g. /seek 20)"),
    BotCommand("seekback", "Seek stream backward (e.g. /seekback 20)"),
    BotCommand("loop", "Loop current stream (e.g. /loop 3)"),
    BotCommand("autoplay", "Toggle autoplay recommended tracks"),
    BotCommand("settings", "Open chat settings (welcome, vc join, etc)"),
    BotCommand("welcome", "Enable/disable welcome banner"),
    BotCommand("vcnotify", "Enable/disable VC join notifications"),
    BotCommand("auth", "Authorize user for bot playback control"),
    BotCommand("unauth", "Remove user from authorized list"),
    BotCommand("authlist", "List authorized users in group"),
    BotCommand("reload", "Refresh group admin list cache"),
    BotCommand("ping", "Check bot latency and uptime"),
    BotCommand("stats", "View bot and system statistics"),
    BotCommand("language", "Change chat language"),
    BotCommand("vps", "Check server disk and storage usage"),
    BotCommand("help", "Show help menu and command guide"),
]

# Private chat commands
PRIVATE_COMMANDS = [
    BotCommand("start", "Start the bot and get info"),
    BotCommand("help", "Show full help menu and guide"),
    BotCommand("settings", "Group settings guide"),
    BotCommand("ping", "Check bot latency and uptime"),
    BotCommand("stats", "View bot and system statistics"),
    BotCommand("language", "Set bot language"),
    BotCommand("vps", "Check server disk and storage usage"),
]

# Default fallback commands
DEFAULT_COMMANDS = [
    BotCommand("play", "Play requested audio track in voice chat"),
    BotCommand("vplay", "Play requested video in voice chat"),
    BotCommand("pause", "Pause currently playing stream"),
    BotCommand("resume", "Resume paused stream"),
    BotCommand("skip", "Skip to next track in queue"),
    BotCommand("stop", "Stop stream and clear queue"),
    BotCommand("queue", "View queue and current playing song"),
    BotCommand("settings", "Open chat music settings"),
    BotCommand("welcome", "Enable/disable welcome banner"),
    BotCommand("vcnotify", "Enable/disable VC join notifications"),
    BotCommand("ping", "Check bot latency and uptime"),
    BotCommand("stats", "View bot and system statistics"),
    BotCommand("help", "Show help menu and command guide"),
    BotCommand("start", "Start the bot"),
]


async def set_suggested_commands(client) -> bool:
    """
    Registers suggested commands with Telegram for autocomplete/menu.
    """
    try:
        await client.set_bot_commands(DEFAULT_COMMANDS, scope=BotCommandScopeDefault())
        await client.set_bot_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
        await client.set_bot_commands(ADMIN_COMMANDS, scope=BotCommandScopeAllChatAdministrators())
        await client.set_bot_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        logger.info("Bot suggested commands registered successfully.")
        return True
    except Exception as err:
        logger.warning(f"Failed to register suggested bot commands: {err}")
        return False
