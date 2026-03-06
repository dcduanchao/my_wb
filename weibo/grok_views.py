import json
import logging
import threading
import time
from io import BytesIO

import requests
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST, require_GET

from minio_util import minio_client
from utils.result_resp import APIResponse
from weibo import wb_header
from weibo.comfyui_models import GrokInfo

logger = logging.getLogger(__name__)


grok_headers = wb_header.grok_auth_headers



proxies = {
    "http": "http://192.168.30.30:7890",
    "https": "http://192.168.30.30:7890"
}

@require_POST
def grok_gen(request):
    body = request.body.decode('utf-8')
    logger.info("grok_image 请求参数  %s", body)
    data = json.loads(body or "{}")

    if not  data:
        return APIResponse.error("参数有误")

    opr_type =  data.get("type")
    prompt = data.get("prompt")
    data.pop("type")

    gi = GrokInfo(opr_type=opr_type,prompt=prompt,params=json.dumps(data,ensure_ascii=False))
    gi.save()
    logger.info("grok_gen save %s",gi)
    if opr_type==2:
        threading.Thread(target=grok_video_result, args=(data,gi,)).start()
    else:

        threading.Thread(target=grok_image_result, args=(data,gi,)).start()


    return APIResponse.success_msg("图片生成中请稍后")


def grok_video_result(data,gi:GrokInfo):

    grok_url = "https://api.x.ai//v1/videos/generations"
    resp= requests.post(grok_url, headers=grok_headers, proxies=proxies, json=data,timeout=120)

    logger.info("grok_video_result code=%s", resp.status_code)

    if resp.status_code != 200:
        data=  resp.json()
        error = data.get("error")
        gi.remakes=error
        gi.save(update_fields=["remakes"])
        return

    request_id = resp.json().get("request_id")
    logger.info("grok_video_result request_id=%s", request_id)
    if request_id is None:
        gi.remakes = "未获取到request_id"
        gi.save(update_fields=["remakes"])
        return
    request_url = f"https://api.x.ai/v1/videos/{request_id}"
    count =0;
    while(True):
        time.sleep(15)
        logger.info("grok_video_result request_url=%s", request_url)
        resp= requests.get(request_url, headers=grok_headers, proxies=proxies, json=data,timeout=120)
        logger.info("grok_video_result code=%s", resp.text)
        if resp.status_code != 200:
            data = resp.json()
            error = data.get("error")
            gi.remakes = error
            gi.save(update_fields=["remakes"])
            break
        # 5分钟
        if count > 20:
            logger.info("count >20 %s",request_url)
            break

        status= resp.json()["status"]
        if status!="done":
            count+=1
            continue

        content_type = "video/mp4"
        v_url=resp.json()["video"]["url"]
        resp = requests.get(v_url, headers=grok_headers, proxies=proxies, timeout=240)

        bio = BytesIO()
        for chunk in resp.iter_content(chunk_size=4096):
            if chunk:
                bio.write(chunk)
        bio.seek(0)
        object_name = v_url.rsplit("/",1)[-1]
        a,b,minio_url = minio_client.upload_bytes_io("grok", object_name, bio, content_type)
        url_infos = []
        url_info = {"url": v_url, "minio_url": minio_url}
        url_infos.append(url_info)
        logger.info("grok_image_result url_infos=%s", url_infos)
        gi.url_infos = json.dumps(url_infos,ensure_ascii=False)
        gi.save(update_fields=["url_infos"])
        break




def grok_image_result(data,gi:GrokInfo):
    grok_url = "https://api.x.ai/v1/images/generations"
    resp= requests.post(grok_url, headers=grok_headers, proxies=proxies, json=data,timeout=120)

    logger.info("grok_image_result code=%s", resp.status_code)
    if resp.status_code != 200:
        data=  resp.json()
        error = data.get("error")
        gi.remakes=error
        gi.save(update_fields=["remakes"])
        return

    datas = resp.json()["data"]
    mime_type=None
    images=[]
    for data in datas:
        url = data.get("url")
        images.append(url)
        type = data.get("mime_type")
        if mime_type is None:
            mime_type = type

    url_infos=[]
    if images:
        for image in images:
            try:
                resp = requests.get(image, headers=grok_headers, proxies=proxies, timeout=120)

                object_name = image.rsplit('/', 1)[-1]
                bio=BytesIO()
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        bio.write(chunk)
                bio.seek(0)
                a,b,minio_url = minio_client.upload_bytes_io("grok", object_name, bio, mime_type)
                url_info= {"url": image, "minio_url": minio_url}
                url_infos.append(url_info)
            except Exception as e:
                logger.error(e)
        logger.info("grok_image_result url_infos=%s", url_infos)
        gi.url_infos = json.dumps(url_infos,ensure_ascii=False)
        gi.save(update_fields=["url_infos"])
    else:
        gi.remakes = "未解析到图片"
        gi.save(update_fields=["remakes"])



@require_GET
def grok_list(request):
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 20))
    opr_type = request.GET.get("type")
    # ✅ 分页
    q = Q()

    # ✅ 模糊查询（包含）
    if opr_type:
        q &= Q(opr_type=int(opr_type))

    queryset = GrokInfo.objects.filter(q).order_by("-id")

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    data = list(page_obj.object_list.values())
    page_data = {
        "total": paginator.count,
        "page": page,
        "page_size": page_size,
        "list": data
    }
    return APIResponse.success_data("成功", page_data)


@require_GET
def grok_delete(request):
    id_str = request.GET.get("id")
    if not id_str:
        return APIResponse.error("id 不能为空")

    try:
        id = int(id_str)
    except ValueError:
        return APIResponse.error("id 必须是整数")

    wi = GrokInfo.objects.filter(id=id).first()
    if wi:
        if wi.url_infos:
            infos = json.loads(wi.url_infos)
            for info in infos:
                url = info["minio_url"]
                if url:
                    filename1 = url.rsplit("/", 1)[-1]
                    minio_client.delete("grok",filename1)
        wi.delete()

    return APIResponse.success_msg("删除成功")
