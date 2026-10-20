# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import enums, types

from anony import app, config, lang
from anony.core.lang import lang_codes


RADHA_MAP = {
    "a": "ᴧ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ",
    "f": "ғ", "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ",
    "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ", "o": "ᴏ",
    "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ",
    "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ",
    "A": "ᴧ", "B": "ʙ", "C": "ᴄ", "D": "ᴅ", "E": "ᴇ",
    "F": "ғ", "G": "ɢ", "H": "ʜ", "I": "ɪ", "J": "ᴊ",
    "K": "ᴋ", "L": "ʟ", "M": "ᴍ", "N": "ɴ", "O": "ᴏ",
    "P": "ᴘ", "Q": "ǫ", "R": "ʀ", "S": "s", "T": "ᴛ",
    "U": "ᴜ", "V": "ᴠ", "W": "ᴡ", "X": "x", "Y": "ʏ", "Z": "ᴢ",
}


def to_radha_style(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    stripped = text.strip()
    if not stripped or stripped in ("▷", "II", "⥁", "‣‣I", "▢", "❐") or "◉" in stripped or "|" in stripped:
        return text

    res = []
    has_letters = False
    for c in text:
        if c in RADHA_MAP:
            res.append(RADHA_MAP[c])
            has_letters = True
        else:
            res.append(c)
    converted = "".join(res).strip()
    if has_letters and not (converted.startswith("˹") and converted.endswith("˼")):
        return f"˹{converted}˼"
    return converted


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup

    def ikb(self, text: str, **kwargs) -> types.InlineKeyboardButton:
        return types.InlineKeyboardButton(text=to_radha_style(text), **kwargs)

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=text,
                        callback_data="cancel_dl",
                        style=enums.ButtonStyle.DANGER,
                    )
                ]
            ]
        )

    def close_key(self, text: str = "Close") -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=text,
                        callback_data="help close",
                        style=enums.ButtonStyle.DANGER,
                    )
                ]
            ]
        )

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        if status:
            keyboard.append(
                [
                    self.ikb(
                        text=status,
                        callback_data=f"controls status {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    )
                ]
            )
        elif timer:
            keyboard.append(
                [
                    self.ikb(
                        text=timer,
                        callback_data=f"controls status {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    )
                ]
            )

        if not remove:
            keyboard.append(
                [
                    self.ikb(
                        text="▷",
                        callback_data=f"controls resume {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="II",
                        callback_data=f"controls pause {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="⥁",
                        callback_data=f"controls replay {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="‣‣I",
                        callback_data=f"controls skip {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="▢",
                        callback_data=f"controls stop {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    ),
                ]
            )
        return self.ikm(keyboard)

    def autoplay_markup(self, chat_id: int, status: bool) -> types.InlineKeyboardMarkup:
        btn_text = "˹ᴛᴜʀɴ ᴏғғ˼" if status else "˹ᴛᴜʀɴ ᴏɴ˼"
        act = "disable" if status else "enable"
        return self.ikm(
            [
                [
                    self.ikb(
                        text=btn_text,
                        callback_data=f"autoplay_toggle {chat_id} {act}",
                        style=enums.ButtonStyle.DANGER if status else enums.ButtonStyle.SUCCESS,
                    ),
                    self.ikb(
                        text="˹ᴄʟᴏsᴇ˼",
                        callback_data="help close",
                        style=enums.ButtonStyle.DANGER,
                    ),
                ]
            ]
        )

    def autoplay_prompt_markup(self, chat_id: int) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    types.InlineKeyboardButton(
                        text="Autoplay",
                        callback_data=f"autoplay_start {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    ),
                ]
            ]
        )

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [
                    self.ikb(
                        text=_lang["back"],
                        callback_data="help back",
                        style=enums.ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text=_lang["close"],
                        callback_data="help close",
                        style=enums.ButtonStyle.DANGER,
                    ),
                ]
            ]
        else:
            cbs = [
                "admins",
                "auth",
                "blist",
                "lang",
                "ping",
                "play",
                "queue",
                "stats",
                "sudo",
            ]
            buttons = [
                self.ikb(
                    text=_lang[f"help_{i}"],
                    callback_data=f"help {cb}",
                    style=enums.ButtonStyle.PRIMARY,
                )
                for i, cb in enumerate(cbs)
            ]
            rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]

        return self.ikm(rows)

    def help_group_key(self, text: str = "Help") -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=text,
                        url=f"https://t.me/{app.username}?start=help",
                        style=enums.ButtonStyle.PRIMARY,
                    )
                ]
            ]
        )

    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()

        buttons = [
            self.ikb(
                text=f"{name} ({code}) {'✔️' if code == _lang else ''}",
                callback_data=f"lang_change {code}",
                style=(
                    enums.ButtonStyle.SUCCESS
                    if code == _lang
                    else enums.ButtonStyle.PRIMARY
                ),
            )
            for code, name in langs.items()
        ]
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=text,
                        url=config.SUPPORT_CHAT,
                        style=enums.ButtonStyle.PRIMARY,
                    )
                ]
            ]
        )

    def play_queued(
        self, chat_id: int, item_id: str = None, _text: str = None
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text="II",
                        callback_data=f"controls pause {chat_id} queued",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="▷",
                        callback_data=f"controls resume {chat_id} queued",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="▢",
                        callback_data=f"controls stop {chat_id} queued",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="‣‣I",
                        callback_data=f"controls skip {chat_id} queued",
                        style=enums.ButtonStyle.DANGER,
                    ),
                ]
            ]
        )

    def queue_markup(
        self, chat_id: int, slidebar: str = None, playing: bool = True
    ) -> types.InlineKeyboardMarkup:
        if not slidebar or not isinstance(slidebar, str) or ("|" not in slidebar and "◉" not in slidebar):
            slidebar = "00:00 | ◉————————— | -00:00"
        return self.ikm(
            [
                [
                    self.ikb(
                        text=slidebar,
                        callback_data=f"controls status {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    )
                ],
                [
                    self.ikb(
                        text="Queue",
                        callback_data=f"queue_list {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="Close",
                        callback_data="help close",
                        style=enums.ButtonStyle.DANGER,
                    ),
                ],
            ]
        )

    def queue_list_markup(
        self, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text="Back",
                        callback_data=f"queue_back {chat_id}",
                        style=enums.ButtonStyle.DANGER,
                    ),
                    self.ikb(
                        text="Close",
                        callback_data="help close",
                        style=enums.ButtonStyle.DANGER,
                    ),
                ]
            ]
        )

    def settings_text(
        self,
        chat_title: str,
        admin_only: bool,
        cmd_delete: bool,
        welcome: bool,
        vc_notify: bool,
        play_thumb: bool,
        language: str,
    ) -> str:
        lang_str = lang_codes.get(language, language)
        return (
            f"<u><b>{chat_title} Settings</b></u>\n\n"
            f"⚙️ <b>Current Chat Configuration:</b>\n"
            f"• <b>Play Mode :</b> <code>{'Admin Only' if admin_only else 'Everyone'}</code>\n"
            f"• <b>Cmd Delete :</b> <code>{'Enabled' if cmd_delete else 'Disabled'}</code>\n"
            f"• <b>Welcome Banner :</b> <code>{'Enabled' if welcome else 'Disabled'}</code>\n"
            f"• <b>VC Join Alert :</b> <code>{'Enabled' if vc_notify else 'Disabled'}</code>\n"
            f"• <b>Play Thumbnail :</b> <code>{'Enabled' if play_thumb else 'Disabled'}</code>\n"
            f"• <b>Language :</b> <code>{lang_str}</code>\n\n"
            f"<i>Click the buttons below to toggle any setting:</i>"
        )

    def settings_markup(
        self,
        lang: dict,
        admin_only: bool,
        cmd_delete: bool,
        language: str,
        chat_id: int,
        welcome: bool = True,
        vc_notify: bool = True,
        play_thumb: bool = True,
    ) -> types.InlineKeyboardMarkup:
        def _btn(status: bool, cb_data: str):
            text = "ENABLED" if status else "DISABLED"
            style = enums.ButtonStyle.SUCCESS if status else enums.ButtonStyle.DANGER
            return self.ikb(text=text, callback_data=cb_data, style=style)

        return self.ikm(
            [
                [
                    self.ikb(
                        text=lang.get("play_mode", "Play Mode") + " ➜",
                        callback_data="settings",
                        style=enums.ButtonStyle.DEFAULT,
                    ),
                    _btn(admin_only, "settings play"),
                ],
                [
                    self.ikb(
                        text=lang.get("cmd_delete", "Cmd Delete") + " ➜",
                        callback_data="settings",
                        style=enums.ButtonStyle.DEFAULT,
                    ),
                    _btn(cmd_delete, "settings delete"),
                ],
                [
                    self.ikb(
                        text="Welcome ➜",
                        callback_data="settings",
                        style=enums.ButtonStyle.DEFAULT,
                    ),
                    _btn(welcome, "settings welcome"),
                ],
                [
                    self.ikb(
                        text="VC Join Msg ➜",
                        callback_data="settings",
                        style=enums.ButtonStyle.DEFAULT,
                    ),
                    _btn(vc_notify, "settings vc_notify"),
                ],
                [
                    self.ikb(
                        text="Play Thumb ➜",
                        callback_data="settings",
                        style=enums.ButtonStyle.DEFAULT,
                    ),
                    _btn(play_thumb, "settings thumb"),
                ],
                [
                    self.ikb(
                        text=lang.get("language", "Language") + " ➜",
                        callback_data="settings",
                        style=enums.ButtonStyle.DEFAULT,
                    ),
                    self.ikb(
                        text=lang_codes.get(language, language),
                        callback_data="language",
                        style=enums.ButtonStyle.PRIMARY,
                    ),
                ],
                [
                    self.ikb(
                        text=lang.get("close", "Close"),
                        callback_data="close",
                        style=enums.ButtonStyle.DANGER,
                    )
                ],
            ]
        )

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        if private:
            rows = [
                [
                    self.ikb(
                        text=lang["add_me"],
                        url=f"https://t.me/{app.username}?startgroup=true",
                        style=enums.ButtonStyle.SUCCESS,
                    )
                ],
                [
                    self.ikb(
                        text=lang["help"],
                        callback_data="help",
                        style=enums.ButtonStyle.PRIMARY,
                    )
                ],
                [
                    self.ikb(
                        text=lang["support"],
                        url=config.SUPPORT_CHAT,
                        style=enums.ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text=lang["channel"],
                        url=config.SUPPORT_CHANNEL,
                        style=enums.ButtonStyle.PRIMARY,
                    ),
                ],
            ]
        else:
            rows = [
                [
                    self.ikb(
                        text=lang["add_me"],
                        url=f"https://t.me/{app.username}?startgroup=true",
                        style=enums.ButtonStyle.SUCCESS,
                    ),
                    self.ikb(
                        text=lang["support"],
                        url=config.SUPPORT_CHAT,
                        style=enums.ButtonStyle.PRIMARY,
                    ),
                ]
            ]
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text="❐",
                        copy_text=link,
                        style=enums.ButtonStyle.DEFAULT,
                    ),
                    self.ikb(
                        text="Youtube",
                        url=link,
                        style=enums.ButtonStyle.DANGER,
                    ),
                ],
            ]
        )

    def vc_notify_markup(self, chat_id: int, status: bool) -> types.InlineKeyboardMarkup:
        toggle_text = "Disable" if status else "Enable"
        toggle_action = "disable" if status else "enable"
        return self.ikm(
            [
                [
                    self.ikb(
                        text=toggle_text,
                        callback_data=f"vcnotify_toggle {chat_id} {toggle_action}",
                    ),
                    self.ikb(
                        text="Close",
                        callback_data="close",
                    ),
                ]
            ]
        )

