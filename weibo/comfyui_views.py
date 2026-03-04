import json
import logging
import os
import threading
import uuid

import requests
from django.core.paginator import Paginator

from django.views.decorators.http import require_POST, require_GET

from minio_util import minio_client
from utils.result_resp import APIResponse
from weibo import wb_header
from weibo.comfyui.comfui_api import upload_input_url, comfy_ui_edit_run, \
    comfy_ui_create_run, reboot_env, comfyui_history, get_seed
from weibo.comfyui.work_flow_info import WorkFlowInfo
from weibo.comfyui_models import ComfyuiImage

logger = logging.getLogger(__name__)

headers = wb_header.headers

@require_GET
def reboot(request):
    try:
        reboot_env()
    except:
        pass
    return APIResponse.success_msg("success")

@require_POST
def comfyui_edit(request):
    file = request.FILES.get("image")
    logger.info("comfyui_edit name=%s ,file.size=%s file.content_type=%s",file.name,file.size,file.content_type)
    prompt = request.POST.get("prompt")
    na_prompt = request.POST.get("na_prompt")

    url_one = None
    if file and file.name:
        re = minio_client.upload_bytes("comfyui", file.name, file.read(),file.content_type)
        a,b,url_one=re

    logger.info("comfyui_edit prompt=%s na_prompt=%s url=%s",prompt,na_prompt,url_one)
    # name,scale=upload_input_url(url_one)
    # logger.info("comfyui_edit name=%s scale=%s ",name,scale)


    image2 = request.FILES.get("image2")
    image3 = request.FILES.get("image3")
    image4 = request.FILES.get("image4")

    image_batch=[]
    if image2:
        logger.info("comfyui_edit image2 name=%s ,file.size=%s file.content_type=%s", image2.name, image2.size, image2.content_type)
        re = minio_client.upload_bytes("comfyui", image2.name, image2.read(), image2.content_type)
        a, b, url = re
        image_batch.append(url)
    if image3:
        logger.info("comfyui_edit image3 name=%s ,file.size=%s file.content_type=%s", image3.name, image3.size,image3.content_type)
        re = minio_client.upload_bytes("comfyui", image3.name, image3.read(), image3.content_type)
        a, b, url = re
        image_batch.append(url)
    if image4:
        logger.info("comfyui_edit image4 name=%s ,file.size=%s file.content_type=%s", image4.name, image4.size,image4.content_type)
        re = minio_client.upload_bytes("comfyui", image4.name, image4.read(), image4.content_type)
        a, b, url = re
        image_batch.append(url)

    logger.info("comfyui_edit image_batch=%s ",image_batch)

    template_name="qwen_edit_all.json"
    if image_batch :
        template_name = "qwen_edit_all_batch.json"



    prompt_id = comfy_ui_edit_run(url_one,prompt,na_prompt,template_name,image_batch)
    if prompt_id is None:
        return  APIResponse.error("修改失败")

    image_batch_str= json.dumps(image_batch)

    ci = ComfyuiImage(
        c_type=1,
        img_url=url_one,
        ref_url=image_batch_str,
        prompt=prompt,
        na_prompt=na_prompt,
        work_flow_name=template_name
    )
    ci.save()

    threading.Thread(target=comfyui_opr_result, args=(prompt_id, ci,)).start()

    return APIResponse.success_msg("修改中请稍后查看")

def comfyui_opr_result(prompt_id, ci:ComfyuiImage):
    img = comfy_ui_minio_result(prompt_id)
    logger.info("comfyui_edit_result  img=%s ",img)

    if img:
        a,b,url=img
        ci.minio_url=url
        ci.save(update_fields=["minio_url"])



def  comfy_ui_minio_result(prompt_id):
    img = comfyui_history(prompt_id)
    logger.info("comfyui_result image = %s", img)

    if img is None:
        logger.error("comfyui_result error id = %s", id)
        return None

    return  minio_client.upload_comfyui_url(img)




@require_GET
def comfyui_edit_list(request):

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 20))
    c_type = request.GET.get("c_type")

    logger.info(
        "records 请求参数 page=%s page_size=%s uname=%s",
        page, page_size, c_type
    )

    # ✅ 分页
    queryset = ComfyuiImage.objects.filter(c_type=c_type).order_by("-id")

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
def comfyui_image_delete(request):
    id_str = request.GET.get("id")
    if not id_str:
        return APIResponse.error("id 不能为空")

    try:
        id = int(id_str)
    except ValueError:
        return APIResponse.error("id 必须是整数")

    wi = ComfyuiImage.objects.filter(id=id).first()
    if wi:
        if wi.minio_url:
            filename1 = wi.minio_url.rsplit("/", 1)[-1]
            minio_client.delete("comfyui",filename1)
        if wi.img_url:
            filename1 = wi.img_url.rsplit("/", 1)[-1]
            minio_client.delete("comfyui",filename1)
        if wi.video_url:
            filename1 = wi.video_url.rsplit("/", 1)[-1]
            minio_client.delete("comfyui",filename1)

        wi.delete()

    return APIResponse.success_msg("删除成功")


def comfyui_create(request):

    prompt = request.POST.get("prompt")
    na_prompt = request.POST.get("na_prompt")

    logger.info("comfyui_edit prompt=%s na_prompt=%s url=%s", prompt, na_prompt)

    wf = WorkFlowInfo("z_image_turbo_16.json")
    wf.prompt = prompt
    wf.na_prompt = na_prompt
    wf.seed = get_seed()

    prompt_id = comfy_ui_create_run(wf)

    if prompt_id is None:
        return APIResponse.error("生成失败")

    ci = ComfyuiImage(
        c_type=0,
        prompt=prompt,
        na_prompt=na_prompt,
        work_flow_name="qwen_edit_all.json"
    )
    ci.save()
    threading.Thread(target=comfyui_opr_result, args=(prompt_id, ci,)).start()
    return APIResponse.success_msg("生成中请稍后查看")


