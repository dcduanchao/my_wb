import json
import os
import threading
import uuid

import requests
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse, JsonResponse


import logging

from django.views.decorators.http import require_GET, require_POST

from minio_util import minio_client
from utils.result_resp import APIResponse
from weibo import wb_header
from weibo.comfyui.comfui_api import build_comfyui_prompt, comfyui_run, comfyui_history, upload_input, upload_input_url
from weibo.models import WbUser, WeiboImages, WeiboUpdateImage
from weibo.wb_image import  get_image1
from weibo.wbapi import get_user_info


headers = wb_header.headers

logger = logging.getLogger(__name__)

def index(request):
    return HttpResponse("Hello, myweb")


def get_image_data(uid):
    threading.Thread(target=get_image1, args=(uid,0)).start()



@require_POST
def crawl(request):
    # print(request.method)
    body = request.body.decode('utf-8')
    logger.info("crawl 请求参数  %s",body)
    data = json.loads(body or "{}")
    uid = data['uid']

    exite = WbUser.objects.filter(uid=uid).exists()
    if exite:
        get_image_data(uid)
        return APIResponse.success_msg("数据用户已存在，抓取图片中...")

    resp=get_user_info(uid)
    if resp is None:
        return APIResponse.error("请求wb失败...")

    logger.info("crawl uid=%s , res=%s",uid,resp.text)
    result = resp.json()
    code = result["ok"]
    if code != 1:
        return APIResponse.error(code)
    data = result.get("data")
    if data is None:
        msg = result.get("message")
        return APIResponse.error(msg)
    user = data.get("user")
    uname = user.get("screen_name")
    avatar = user.get("avatar_hd")
    if avatar is None:
        avatar = user.get("avatar_large")

    if avatar :
        response = requests.get(avatar, headers=headers, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type")
        re = minio_client.upload_bytes("weibo", f'{uname}.jpg', response.content, content_type)
        status_code, msg, url1 = re

    logger.info("crawl uid=%s name = %s ,avatar=%s",uid,uname,avatar)


    wb_user=WbUser(u_name=uname,uid=uid,avatar=url1)
    wb_user.save()
    get_image_data(uid)

    return APIResponse.success_msg("数据抓取中")




@require_GET
def records(request):

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 20))
    uname = request.GET.get("uname")

    logger.info(
        "records 请求参数 page=%s page_size=%s uname=%s",
        page, page_size, uname
    )

    q = Q()


    # ✅ 模糊查询（包含）
    if uname:
        q &= Q(u_name__icontains=uname)
    # ✅ 分页
    queryset = WbUser.objects.filter(q).order_by("-id")

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    data = list(page_obj.object_list.values())
    page_data={
        "total": paginator.count,
        "page": page,
        "page_size": page_size,
        "list": data
    }
    return APIResponse.success_data("成功",page_data)


@require_GET
def album(request):
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 20))
    uid = request.GET.get("uid")

    logger.info(
        "records 请求参数 page=%s page_size=%s uid=%s",
        page, page_size, uid
    )

    queryset = WeiboImages.objects.filter(uid=uid)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    data = list(page_obj.object_list.values("id", "uid","pid", "pic_type", "minio_url","minio_video"))
    page_data = {
        "total": paginator.count,
        "page": page,
        "page_size": page_size,
        "list": data
    }
    return APIResponse.success_data("成功", page_data)


@require_POST
def album_update(request):
    body = request.body.decode('utf-8')
    logger.info("album_update 请求参数  %s", body)
    data = json.loads(body or "{}")
    id = data['id']

    wb = WeiboImages.objects.filter(id=id).first()
    minio_url = wb.minio_url
    upload_image_name,scale = upload_input_url(minio_url)
    if not upload_image_name:
        return APIResponse.error("图片上传失败")


    prompt_text = data.get("prompt")
    na_prompt = data.get("na_prompt")


    work = build_comfyui_prompt(prompt_text, upload_image_name,scale,na_prompt)

    logger.info("album_update work= %s",json.dumps(work, indent=4, ensure_ascii=False))



    prompt_id = comfyui_run(work)
    logger.info("album_update prompt_id=%s",prompt_id)

    if prompt_id is None:
        logger.error("album_update error id = %s",id)
        return APIResponse.error("修改失败")
    threading.Thread(target=comfyui_result, args=(prompt_id,id,)).start()
    return APIResponse.success_msg("修改中请稍后查看")



def comfyui_result(prompt_id,id):
    img = comfyui_history(prompt_id)
    logger.info("comfyui_result image = %s",img)

    if img is None:
        logger.error("comfyui_result error id = %s",id)
        return

    wb = WeiboImages.objects.filter(id=id).first()

    response = requests.get(img, timeout=30)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type")

    filename = None
    content_disposition = response.headers.get("Content-Disposition")
    if content_disposition:
        # 通常 Content-Disposition 类似：attachment; filename="ComfyUI_00019_.png"
        parts = content_disposition.split(";")
        for part in parts:
            part = part.strip()
            if part.startswith("filename="):
                filename = part.split("=", 1)[1].strip('"')
                break
    if not filename :
        file_ext=".png"
        content_type="image/png"
    else:
       file_ext = os.path.splitext(filename)[1]

    if not content_type:
        content_type="image/png"

    random_str = uuid.uuid4().hex[:16]

    filename1=f"{random_str}{file_ext}"

    re = minio_client.upload_bytes("weibo", filename1, response.content, content_type)
    status_code, msg, url = re
    WeiboUpdateImage(uid=wb.uid,update_id=id,minio_url=url).save()
    logger.info("comfyui_result update_id=%s success",id)



@require_GET
def album_update_record(request):
    id_str = request.GET.get("id")
    if not id_str:
        return APIResponse.error("id 不能为空")

    try:
        id = int(id_str)
    except ValueError:
        return APIResponse.error("id 必须是整数")

    update_images = WeiboUpdateImage.objects.filter(update_id=id).values("id","minio_url")

    # 提取 minio_url，如果为空则忽略
    # all_urls = [img.minio_url for img in update_images if img.minio_url]

    update_images_list = list(update_images)

    return APIResponse.success_data("成功",update_images_list)


@require_GET
def album_delete(request):
    id_str = request.GET.get("id")
    if not id_str:
        return APIResponse.error("id 不能为空")

    try:
        id = int(id_str)
    except ValueError:
        return APIResponse.error("id 必须是整数")

    wi = WeiboImages.objects.filter(id=id).first()
    if wi:
        if wi.minio_url:
            filename1 = wi.minio_url.rsplit("/", 1)[-1]
            minio_client.delete("weibo",filename1)
        if wi.minio_video:
            filename2 = wi.minio_video.rsplit("/", 1)[-1]
            minio_client.delete("weibo", filename2)
        wi.delete()

        update_images= WeiboUpdateImage.objects.filter(update_id=id)

        for update_image in update_images:
            if update_image.minio_url:
                filename = update_image.minio_url.rsplit("/", 1)[-1]
                minio_client.delete("weibo", filename)
            update_image.delete()

    return APIResponse.success_msg("删除成功")


@require_GET
def album_record_delete(request):
    id_str = request.GET.get("id")
    if not id_str:
        return APIResponse.error("id 不能为空")

    try:
        id = int(id_str)
    except ValueError:
        return APIResponse.error("id 必须是整数")

    wi = WeiboUpdateImage.objects.filter(id=id).first()
    if wi:
        if wi.minio_url:
            filename1 = wi.minio_url.rsplit("/", 1)[-1]
            minio_client.delete("weibo",filename1)
        wi.delete()

    return APIResponse.success_msg("删除成功")