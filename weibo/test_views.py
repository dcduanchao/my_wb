import json
import logging

import requests
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from minio_util import minio_client
from weibo import wb_header
from weibo.comfyui.comfui_api import upload_input_url

logger = logging.getLogger(__name__)

headers = wb_header.headers

@require_POST
def upload_local_file(request):
    file = request.FILES.get("file")
    logger.info("upload_local_file name=%s ,file.size=%s file.content_type=%s",file.name,file.size,file.content_type)
    url = minio_client.upload_bytes("weibo", file.name, file.read(),file.content_type)
    print(url)
    return HttpResponse("aaa")


@require_POST
def upload_from_url(request):
    body = request.body.decode('utf-8')
    data = json.loads(body or "{}")
    im_url = data.get("url")
    name = data.get("name")
    response = requests.get(im_url, headers=headers, timeout=30)
    response.raise_for_status()
    content_type=response.headers.get("Content-Type")
    print(content_type)
    re = minio_client.upload_bytes("weibo", name, response.content,content_type)
    print(re)
    status_code ,msg,url = re
    return HttpResponse(url)


@require_POST
def upload_delete(request):
    body = request.body.decode('utf-8')
    data = json.loads(body or "{}")
    im_url = data.get("url")
    filename = im_url.rsplit("/", 1)[-1]
    re = minio_client.delete("weibo" ,filename)

    return HttpResponse(re)


@require_POST
def comfyui_upload_url(request):
    body = request.body.decode('utf-8')
    data = json.loads(body or "{}")
    im_url = data.get("url")
    name = data.get("name")
    rs = upload_input_url(im_url,name)
    return HttpResponse(rs)

