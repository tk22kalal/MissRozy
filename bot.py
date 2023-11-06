import os
import asyncio
import traceback
from pyrogram import Client, filters, idle
from pyrogram.errors import UserNotParticipant, FloodWait, QueryIdInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from binascii import Error
from configs import Config
from handlers.database import db
from handlers.add_user_to_db import add_user_to_database
from handlers.send_file import send_media_and_reply
from handlers.helpers import b64_to_str, str_to_b64
from handlers.check_user_status import handle_user_status
from handlers.force_sub_handler import handle_force_sub, get_invite_link
from handlers.broadcast_handlers import main_broadcast_handler
from handlers.save_media import save_media_in_channel, save_batch_media_in_channel
from util.human_readable import humanbytes
from urllib.parse import quote_plus
from util.file_properties import get_name, get_hash, get_media_file_size
from pyrogram import Client, __version__
from handlers.helpers import decode, get_messages
from pyrogram.enums import ParseMode
import sys
from util.keepalive import ping_server
from lazybot import Bot
from lazybot.clients import initialize_clients
from aiohttp import web
from handlers import web_server

MediaList = {}
PORT = "8080"


@Bot.on_message(filters.private)
async def handle_private_messages(bot: Client, cmd: Message):
    await handle_user_status(bot, cmd)

@Bot.on_message(filters.command("start") & filters.private)
async def start(bot: Client, cmd: Message):
    if cmd.from_user.id in Config.BANNED_USERS:
        await cmd.reply_text("ꜱᴏʀʀʏ, ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ.")
        return

    if Config.UPDATES_CHANNEL is not None:
        back = await handle_force_sub(bot, cmd)
        if back == 400:
            return

    usr_cmd = cmd.text.split("_", 1)[-1]

    if usr_cmd == "/start":
        await add_user_to_database(bot, cmd)
        if Config.LAZY_MODE:
            await cmd.reply_photo(photo=lazy_pic,
                caption=Config.LAZY_HOME_TEXT.format(cmd.from_user.first_name, cmd.from_user.id),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🍿supp⊕r† gr⊕up", url="https://t.me/LazyDeveloperSupport"),
                        InlineKeyboardButton("🔊ß⊕†s chαηηεl", url="https://t.me/LazyDeveloper")
                    ],
                    [
                        InlineKeyboardButton("🤖Aß⊕ut ß⊕†", callback_data="aboutbot"),
                        InlineKeyboardButton("♥️Aß⊕ut Đ€V", callback_data="aboutdevs")
                    ],
                    [
                        InlineKeyboardButton("⎝⎝✧✧ ᴡᴀᴛᴄʜ ᴛᴜᴛᴏʀɪᴀʟ ✧✧⎠⎠", url="https://youtu.be/Rtjyz3lEZwE")
                    ]
                ]))
        else:
            await cmd.reply_photo(photo=lazy_pic,
                caption=Config.HOME_TEXT.format(cmd.from_user.first_name, cmd.from_user.id),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🍿supp⊕r† gr⊕up", url="https://t.me/LazyDeveloperSupport"),
                        InlineKeyboardButton("🔊ß⊕†s chαηηεl", url="https://t.me/LazyDeveloper")
                    ],
                    [
                        InlineKeyboardButton("🤖Aß⊕ut ß⊕†", callback_data="aboutbot"),
                        InlineKeyboardButton("♥️Aß⊕ut Đ€V", callback_data="aboutdevs")
                    ],
                    [
                        InlineKeyboardButton("⎝⎝✧✧ ᴡᴀᴛᴄʜ ᴛᴜᴛᴏʀɪᴀʟ ✧✧⎠⎠", url="https://youtu.be/Rtjyz3lEZwE")
                    ]
                ]))
    else:
        try:
            try:
                file_id = int(b64_to_str(usr_cmd).split("_")[-1])
            except (Error, UnicodeDecodeError):
                file_id = int(usr_cmd.split("_")[-1])

            GetMessage = await bot.get_messages(chat_id=Config.DB_CHANNEL, message_ids=file_id)
            message_ids = []

            if GetMessage.text:
                message_ids = GetMessage.text.split(" ")
                _response_msg = await cmd.reply_text(
                    text=f"**Total Files:** `{len(message_ids)}`",
                    quote=True,
                    disable_web_page_preview=True
                )
            else:
                message_ids.append(int(GetMessage.id))

            for i in range(len(message_ids)):
                await send_media_and_reply(bot, user_id=cmd.from_user.id, file_id=int(message_ids[i]))

        except Exception as err:
            print(err)
            await cmd.reply_text(f"ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ.!\n\n**Error:** `{err}`")

@Bot.on_message(filters.private & filters.command("broadcast") & filters.user(Config.BOT_OWNER) & filters.reply)
async def broadcast_handler_open(_, m: Message):
    await main_broadcast_handler(m, db)

@Bot.on_message(filters.private & filters.command("status") & filters.user(Config.BOT_OWNER))
async def sts(_, m: Message):
    total_users = await db.total_users_count()
    await m.reply_text(
        text=f"**ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ ɪɴ ᴅʙ:** `{total_users}`",
        quote=True
    )

@Bot.on_message(filters.private & filters.command("ban_user") & filters.user(Config.BOT_OWNER))
async def ban(c: Client, m: Message):
    if len(m.command) == 1:
        await m.reply_text(
            f"ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ʙᴀɴ ᴀɴʏ ᴜꜱᴇʀ ꜰʀᴏᴍ ᴛʜᴇ ʙᴏᴛ.\n\n"
            f"Usage:\n\n"
            f"`/ban_user user_id ban_duration ban_reason`\n\n"
            f"Eg: `/ban_user 1234567 28 You misused me.`\n"
            f"This will ban user with id `1234567` for `28` days for the reason `You misused me`.",
            quote=True
        )
        return

    try:
        user_id = int(m.command[1])
        ban_duration = int(m.command[2])
        ban_reason = ' '.join(m.command[3:])
        ban_log_text = f"BΔnninǤ user {user_id} FФЯ {ban_duration} ᴅᴀʏꜱ ꜰᴏʀ ᴛʜᴇ ʀᴇᴀꜱᴏɴ {ban_reason}."
        try:
            await c.send_message(
                user_id,
                f"ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ ꜰᴏʀ **{ban_duration}** ᴅᴀʏ(ꜱ) ꜰᴏʀ ᴛʜᴇ ʀᴇᴀꜱᴏɴ __{ban_reason}__ \n\n"
                f"**Message from the admin**"
            )
            ban_log_text += '\n\nᴜꜱᴇʀ ɴᴏᴛɪ꜓ɪᴇᴅ ꜱᴜᴄᴄᴇ꜓ꜱ꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓! \n\n`{traceback.format_exc()}`"

        await db.ban_user(user_id, ban_duration, ban_reason)
        print(ban_log_text)
        await m.reply_text(
            ban_log_text,
            quote=True
        )
    except:
        traceback.print_exc()
        await m.reply_text(
            f"Error occoured! Traceback given below\n\n`{traceback.format_exc()}`",
            quote=True
        )
@Bot.on_message(filters.private & filters.command("unban_user") & filters.user(Config.BOT_OWNER))
async def unban(c: Client, m: Message):
    if len(m.command) == 1:
        await m.reply_text(
            f"ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ᴜɴʙᴀɴ ᴀɴʏ ᴜꜱᴇʀ.\n\n"
            f"Usage:\n\n`/unban_user user_id`\n\n"
            f"Eg: `/unban_user 1234567`\n"
            f"ᴛʜɪꜱ ᴡɪʟʟ ᴜɴʙᴀɴ ᴜꜱᴇʀ ᴡɪᴛʜ ɪᴅ `1234567`.",
            quote=True
        )
        return

    try:
        user_id = int(m.command[1])
        unban_log_text = f"ᴜɴʙᴀɴɴɪɴɢ ᴜꜱᴇʀ {user_id}"
        try:
            await c.send_message(
                user_id,
                f"ʏᴏᴜʀ ʙᴀɴ ᴡᴀꜱ ʟɪꜛᴛᴇᴅ!"
            )
            unban_log_text += '\n\nᴜꜱᴇʀ ɴᴏᴛɪ꜓ɪᴇᴅ ꜱᴜꜛ꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓꜓! \n\n`{traceback.format_exc()}`"
        await db.remove_ban(user_id)
        print(unban_log_text)
        await m.reply_text(
            unban_log_text,
            quote=True
        )
    except:
        traceback.print_exc()
        await m.reply_text(
            f"Error occurred! Traceback given below\n\n`{traceback.format_exc()}`",
            quote=True
        )

@Bot.on_message(filters.private & filters.command("banned_users") & filters.user(Config.BOT_OWNER))
async def _banned_users(_, m: Message):
    all_banned_users = await db.get_all_banned_users()
    banned_usr_count = 0
    text = ''

    async for banned_user in all_banned_users:
        user_id = banned_user['id']
        ban_duration = banned_user['ban_status']['ban_duration']
        banned_on = banned_user['ban_status']['banned_on']
        ban_reason = banned_user['ban_status']['ban_reason']
        banned_usr_count += 1
        text += f"> **user_id**: `{user_id}`, **Ban Duration**: `{ban_duration}`, " \
                f"**Banned on**: `{banned_on}`, **Reason**: `{ban_reason}`\n\n"
    reply_text = f"Total banned user(s): `{banned_usr_count}`\n\n{text}"
    
    if len(reply_text) > 4096:
        with open('banned-users.txt', 'w') as f:
            f.write(reply_text)
        await m.reply_document('banned-users.txt', True)
        os.remove('banned-users.txt')
        return
    await m.reply_text(reply_text, True)

@Bot.on_message(filters.private & filters.command("clear_batch"))
async def clear_user_batch(bot: Client, m: Message):
    MediaList[f"{str(m.from_user.id)}"] = []
    await m.reply_text("ᴄʟᴇᴀʀᴇᴅ ʏᴏᴜʀ ʙᴀᴛᴄʜ ꜰɪʟᴇꜱ ꜱᴜᴄᴄᴇꜱꜱꜴʟʟʏ!")

@Bot.on_callback_query()
async def button(bot: Client, cmd: CallbackQuery):
    cb_data = cmd.data
    if "aboutbot" in cb_data:
        await cmd.message.edit(
            Config.ABOUT_BOT_TEXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("⚡️SФUЯCΞ CФDΞS ФF ß⊕Γ",
                                            url="https://github.com/LazyDeveloperr/MissRozy")
                    ],
                    [
                        InlineKeyboardButton("GФ HФMΞ", callback_data="gotohome"),
                        InlineKeyboardButton("♥️Aß⊕ut Đ€V", callback_data="aboutdevs")
                    ]
                ]
            )
        )

    elif "aboutdevs" in cb_data:
        await cmd.message.edit(
            Config.ABOUT_DEV_TEXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("⚡️SФUЯCΞ CФDΞS ФF ß⊕Γ",
                                            url="https://github.com/LazyDeveloperr/MissRozy")
                    ],
                    [
                        InlineKeyboardButton("🤖Aß⊕ut ß⊕t", callback_data="aboutbot"),
                        InlineKeyboardButton("🥷GФ HФMΞ", callback_data="gotohome")
                    ]
                ]
            )
        )

    elif "gotohome" in cb_data:
        if Config.LAZY_MODE == True:
            await cmd.message.edit(
                Config.LAZY_HOME_TEXT.format(cmd.message.chat.first_name, cmd.message.chat.id),
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("🍿supp⊕r† gr⊕up", url="https://t.me/LazyDeveloperSupport"),
                            InlineKeyboardButton("🔊ß⊕ts Channel", url="https://t.me/LazyDeveloper")
                        ],
                        [
                            InlineKeyboardButton("🤖Aß⊕ut ß⊕t", callback_data="aboutbot"),
                            InlineKeyboardButton("♥️Aß⊕ut Đ€V", callback_data="aboutdevs")
                        ],
                        [
                            InlineKeyboardButton("⎝⎝✧✧ ᴡᴀᴛᴄʜ ᴛᴜᴛᴏʀɪᴀʟ ✧✧⎠⎠", url="https://youtu.be/Rtjyz3lEZwE")
                        ]
                    ]
                )
            )
        else:
            await cmd.message.edit(
                Config.HOME_TEXT.format(cmd.message.chat.first_name, cmd.message.chat.id),
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("🍿supp⊕r† gr⊕up", url="https://t.me/LazyDeveloperSupport"),
                            InlineKeyboardButton("🔊ß⊕ts Channel", url="https://t.me/LazyDeveloper")
                        ],
                        [
                            InlineKeyboardButton("🤖Aß⊕ut ß⊕t", callback_data="aboutbot"),
                            InlineKeyboardButton("♥️Aß⊕ut Đ€V", callback_data="aboutdevs")
                        ],
                        [
                            InlineKeyboardButton("⎝⎝✧✧ ᴡᴀᴛᴄʜ ᴛᴜᴛᴏʀɪᴀʟ ✧✧⎠⎠", url="https://youtu.be/Rtjyz3lEZwE")
                        ]
                    ]
                )
            )

    elif "refreshForceSub" in cb_data:
        if Config.UPDATES_CHANNEL:
            if Config.UPDATES_CHANNEL.startswith("-100"):
                channel_chat_id = int(Config.UPDATES_CHANNEL)
            else:
                channel_chat_id = Config.UPDATES_CHANNEL
            try:
                user = await bot.get_chat_member(channel_chat_id, cmd.message.chat.id)
                if user.status == "kicked":
                    await cmd.message.edit(
                        text="ꜱᴏʀʀʏ ꜱɪʀ, ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ᴛᴏ ᴜꜱᴇ ᴍᴇ. ᴄᴏɴᴛᴀᴄᴛ ᴍʏ [Support Group](https://t.me/LazyDeveloperSupport).",
                        disable_web_page_preview=True
                    )
                    return
            except UserNotParticipant:
                invite_link = await get_invite_link(channel_chat_id)
                await cmd.message.edit(
                    text="**ʏᴏᴜ ꜱᴛɪʟʟ ᴅɪᴅɴ'ᴛ ᴊᴏɪɴ ☹️, ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴍʏ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ!**\n\n"
                    "ᴅᴜᴇ ᴛᴏ ᴏᴠᴇʀʟᴏᴀᴅ, ᴏɴʟʏ ᴄʜᴀɴɴᴇʟ ꜱᴜʙꜱᴄʀɪʙᴇʀꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("▌│ 𝙅𝙤𝙞𝙣 𝙐𝙥𝙙𝙖𝙩𝙚𝙨 𝘾𝙝𝙖𝙣𝙣𝙚𝙡 ║║", url=invite_link.invite_link)
                            ],
                            [
                                InlineKeyboardButton("🔄 Refresh 🔄", callback_data="refreshmeh")
                            ]
                        ]
                    )
                )
                return
            except Exception:
                await cmd.message.edit(
                    text="ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. ᴄᴏɴᴛᴀᴴᴛ ᴍʏ [Support Group](https://t.me/LazyDeveloperSupport).",
                    disable_web_page_preview=True
                )
                return
        
Bot.run()
