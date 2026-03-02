import copy
import json
import os
import random
import time
from io import BytesIO

from PIL import Image

import requests

import logging

logger = logging.getLogger()

## url 上传
def upload_input_url(url,name=None):

    resp = requests.get(url)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type")
    if content_type is None:
        sub = url.rsplit(".", 1)[-1]
        if sub=="jpg" or sub=="jpeg":
            content_type = "image/jpeg"
        else:
            content_type = f"image/{sub}"

    image_bytes = BytesIO(resp.content)

    # image_bytes = BytesIO()
    # for chunk in resp.iter_content(chunk_size=8192):
    #     if chunk:
    #         image_bytes.write(chunk)
    # image_bytes.seek(0)


    if name is None:
        name = url.rsplit("/", 1)[-1]

    COMFY_URL = "http://192.168.90.85:8188/upload/image"
    logger.info("upload_input_url param %s %s ",name,content_type)
    files = {
        "image": (name, image_bytes, content_type)  # (文件名, 文件对象, MIME)
    }

    data = {
        "type": "input"  # 必须
    }

    upload_resp = requests.post(COMFY_URL, files=files, data=data)
    upload_result = upload_resp.json()

    ## 缩放图片 不然太慢
    img = Image.open(image_bytes)
    MAX_WIDTH, MAX_HEIGHT = 1024, 1024
    # 2. 获取原图大小
    w, h = img.size
    # 3. 根据最大尺寸计算缩放比例（等比缩放）
    scale_w = MAX_WIDTH / w
    scale_h = MAX_HEIGHT / h
    scale = min(scale_w, scale_h, 1.0)

    logger.info("upload_input_url result %s scale=%s", upload_result, scale)

    return upload_result.get("name"),scale


# 二进制上传comfui
def upload_input(image_name,image_bytes,image_type):

    COMFY_URL = "http://192.168.90.85:8188/upload/image"
    files = {
        "image": (image_name, image_bytes,image_type)  # (文件名, 文件对象, MIME)
    }
    data = {
        "type": "input"  # 必须
    }
    upload_resp = requests.post(COMFY_URL, files=files, data=data)
    upload_result = upload_resp.json()
    logger.info("upload_input result %s ", upload_result)
    return upload_result.get("name")


# 替换工作流
def build_comfyui_prompt(
    prompt_text,
    upload_image_name,
    scale=1,
    negative_prompt=None,
    template_json='qwen_edit_all.json',
    seed=None
):
    if seed is None:
        seed = random.randint(10 ** 14, 10 ** 15 - 1)

    if not negative_prompt :
        negative_prompt = ""   # 如果为空或None，自动变空字符串

    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, template_json)

    with open(template_path, 'r', encoding='utf-8') as f:
        template = json.load(f)

    workflow = copy.deepcopy(template)

    # 正向提示词
    workflow["prompt"]["2"]["inputs"]["prompt"] = prompt_text

    # seed
    workflow["prompt"]["4"]["inputs"]["seed"] = seed

    # 负向提示词（如果节点存在才设置）
    workflow["prompt"]["5"]["inputs"]["text"] = negative_prompt

    workflow["prompt"]["11"]["inputs"]["scale_by"] = scale
    # 上传图片
    workflow["prompt"]["14"]["inputs"]["image"] = upload_image_name

    logger.info("build_comfyui_prompt workflow %s", workflow)

    return workflow


#执行工作流

def comfyui_run(workflow):
    logger.info("comfyui workflow %s", workflow)
    try:
        url ="http://192.168.90.85:8188/prompt"
        reps = requests.post(url, json=workflow)
        reps.raise_for_status()
        logger.info("comfyui_run workflow result %s", reps.json())

        return  reps.json().get("prompt_id")
    except Exception as e:
        logger.exception(e)

    return None


#执行结果图片
def comfyui_history(prompt_id,max_wait=600):
    image_url=None
    url =f"http://192.168.90.85:8188/history/{prompt_id}"

    start_time = time.time()
    while True:

        logger.info("comfyui_history url %s", url)
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            if time.time() - start_time > max_wait:
                raise TimeoutError("等待 ComfyUI 历史记录超时")
            time.sleep(10)
            continue

        task_data = data.get(prompt_id)
        if not task_data:
            time.sleep(10)
            continue

        # 确保任务完成
        status = task_data.get("status", {})
        if not status.get("completed", False):
            if time.time() - start_time > max_wait:
                raise TimeoutError("ComfyUI 任务未完成，超时退出")
            time.sleep(10)
            continue

        images = task_data["outputs"]["12"]["images"]
        for img in images:
            filename = img["filename"]
            subfolder = img["subfolder"]
            type_ = img["type"]
            logger.info (f"生成图片: {filename}, 子目录: {subfolder}, 类型: {type_}")
            # 构造 URL 访问图片（假设 ComfyUI 在 192.168.90.85:8188）
            image_url = f"http://192.168.90.85:8188/view?filename={filename}&type={type_}&subfolder={subfolder}"
            break
        if image_url:
            break

    return image_url




