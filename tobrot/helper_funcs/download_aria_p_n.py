#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) Shrimadhav U K

# the logging things
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

import asyncio
import os
from tobrot.helper_funcs.upload_to_tg import upload_to_tg
from tobrot.helper_funcs.create_compressed_archive import create_archive

from tobrot import (
    AUTH_CHANNEL,
    DOWNLOAD_LOCATION,
    EDIT_SLEEP_TIME_OUT
)

def add_url(aria_instance, text_url, c_file_name):
    options = None
    # if c_file_name is not None:
    #     options = {
    #         "dir": c_file_name
    #     }
    uris = [text_url]
    # Add URL Into Queue
    try:
        download = aria_instance.add_uris(
            uris,
            options=options
        )
    except Exception as e:
        return False, "**FAILED** \n" + str(e) + " \nPlease do not send SLOW links. Read /help"
    else:
        return True, "" + download.gid + ""


async def call_apropriate_function(
    aria_instance,
    incoming_link,
    c_file_name,
    sent_message_to_update_tg_p,
    is_zip
):
    if incoming_link.startswith("magnet:"):
        sagtus, err_message = add_magnet(aria_instance, incoming_link, c_file_name)
    else:
        sagtus, err_message = add_url(aria_instance, incoming_link, c_file_name)
    if not sagtus:
        return sagtus, err_message
    LOGGER.info(err_message)
    # https://stackoverflow.com/a/58213653/4723940
    await check_progress_for_dl(
        aria_instance,
        err_message,
        sent_message_to_update_tg_p,
        None
    )
    file = aria_instance.get_download(err_message)
    to_upload_file = file.name
    #
    if is_zip:
        # first check if current free space allows this
        # ref: https://github.com/out386/aria-telegram-mirror-bot/blob/master/src/download_tools/aria-tools.ts#L194
        # archive the contents
        check_if_file = await create_archive(to_upload_file)
        if check_if_file is not None:
            to_upload_file = check_if_file
    #
    response = {}
    LOGGER.info(response)
    user_id = sent_message_to_update_tg_p.reply_to_message.from_user.id
    final_response = await upload_to_tg(
        sent_message_to_update_tg_p,
        to_upload_file,
        user_id,
        response
    )
    LOGGER.info(final_response)
    message_to_send = ""
    for key_f_res_se in final_response:
        local_file_name = key_f_res_se
        message_id = final_response[key_f_res_se]
        channel_id = str(AUTH_CHANNEL)[4:]
        private_link = f"https://t.me/c/{channel_id}/{message_id}"
        message_to_send += "👉 <a href='"
        message_to_send += private_link
        message_to_send += "'>"
        message_to_send += local_file_name
        message_to_send += "</a>"
        message_to_send += "\n"
    if message_to_send != "":
        mention_req_user = f"<a href='tg://user?id={user_id}'>Your Requested Files</a>\n\n"
        message_to_send = mention_req_user + message_to_send
        message_to_send = message_to_send + "\n\n" + "#uploads"
    else:
        message_to_send = "<i>FAILED</i> to upload files. 😞😞"
    await sent_message_to_update_tg_p.reply_to_message.reply_text(
        text=message_to_send,
        quote=True,
        disable_web_page_preview=True
    )
    return True, None


# https://github.com/jaskaranSM/UniBorg/blob/6d35cf452bce1204613929d4da7530058785b6b1/stdplugins/aria.py#L136-L164
async def check_progress_for_dl(aria2, gid, event, previous_message):
    try:
        file = aria2.get_download(gid)
        complete = file.is_complete
        if not complete:
            if not file.error_message:
                msg = ""
                # sometimes, this weird https://t.me/c/1220993104/392975
                # error creeps up
                # TODO: temporary workaround
                downloading_dir_name = "N/A"
                try:
                    downloading_dir_name = str(download.name)
                except:
                    pass
                #
                msg = f"\nDownloading File: `{downloading_dir_name}`"
                msg += f"\nSpeed: {file.download_speed_string()} 🔽 / {file.upload_speed_string()} 🔼"
                msg += f"\nProgress: {file.progress_string()}"
                msg += f"\nTotal Size: {file.total_length_string()}"
                # msg += f"\nStatus: {file.status}"
                msg += f"\nETA: {file.eta_string()}"
                msg += f"\n<code>/cancel {gid}</code>"
                # LOGGER.info(msg)
                if msg != previous_message:
                    await event.edit(msg)
                    previous_message = msg
            else:
                msg = file.error_message
                await event.edit(f"`{msg}`")
                return False
            await asyncio.sleep(EDIT_SLEEP_TIME_OUT)
            await check_progress_for_dl(aria2, gid, event, previous_message)
        else:
            await event.edit(f"File Downloaded Successfully: `{file.name}`")
            return True
    except Exception as e:
        LOGGER.info(str(e))
        if " not found" in str(e) or "'file'" in str(e):
            await event.edit("Download Canceled :\n`{}`".format(file.name))
            return False
        elif " depth exceeded" in str(e):
            file.remove(force=True)
            await event.edit("Download Auto Canceled :\n`{}`\nYour Torrent/Link is Dead.".format(file.name))
            return False
        else:
            LOGGER.info(str(e))
            await event.edit("<u>error</u> :\n`{}` \n\n#error".format(str(e)))
            return
# https://github.com/jaskaranSM/UniBorg/blob/6d35cf452bce1204613929d4da7530058785b6b1/stdplugins/aria.py#L136-L164


async def check_metadata(aria2, gid):
    file = aria2.get_download(gid)
    LOGGER.info(file)
    if not file.followed_by_ids:
        # https://t.me/c/1213160642/496
        return None
    new_gid = file.followed_by_ids[0]
    LOGGER.info("Changing GID " + gid + " to " + new_gid)
    return new_gid
