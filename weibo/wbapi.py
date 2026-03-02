import logging

import requests

import json
from . import wb_header

from django.template.context_processors import request

logger = logging.getLogger(__name__)


headers=wb_header.headers

def get_user_info(uid):
    url = f"https://weibo.com/ajax/profile/info?uid={uid}"
    try:

        logger.info("get_user_info url= %s", url)
        resp = requests.get(url,headers=headers,timeout=30)
        return resp
    except:
        logger.exception("get_user_info error url= %s", url)
    return None


def get_user_uid_album(uid, sinceid=0):

    url = f'https://weibo.com/ajax/profile/getImageWall?uid={uid}&sinceid={sinceid}'
    try:
        logger.info("get_user_uid_album url= %s", url)
        resp = requests.get(url, headers=headers, timeout=30)
        return resp
    except:
        logger.exception("get_user_uid_album error url= %s", url)
    return None

