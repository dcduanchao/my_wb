
import json
import os
import random
import time
from io import BytesIO
from PIL import Image
import requests
import logging

from weibo.comfyui.work_flow_info import  template_dict_replace, WorkFlowInfo

logger = logging.getLogger()


def reboot_env():
    url ="http://192.168.90.85:8188/api/manager/reboot"
    requests.get(url)


def get_scale(image_bytes):
    ## 缩放图片 不然太慢
    img = Image.open(image_bytes)
    MAX_WIDTH, MAX_HEIGHT = 1024, 1024
    # 2. 获取原图大小
    w, h = img.size
    # 3. 根据最大尺寸计算缩放比例（等比缩放）
    scale_w = MAX_WIDTH / w
    scale_h = MAX_HEIGHT / h
    scale = min(scale_w, scale_h, 1)

    return f"{scale:.1f}"


def get_seed():
    return str(random.randint(10 ** 13, 10 ** 15 - 1))


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

    scale = get_scale(image_bytes)

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

    scale = get_scale(image_bytes)
    upload_resp = requests.post(COMFY_URL, files=files, data=data)
    upload_result = upload_resp.json()
    logger.info("upload_input result %s ", upload_result)
    return upload_result.get("name"),scale



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

        if  status.get("status_str")=="error":
            logger.info("comfyui_history 执行error=%s",url)
            break

        if not status.get("completed", False):
            if time.time() - start_time > max_wait:
                raise TimeoutError("ComfyUI 任务未完成，超时退出")
            time.sleep(10)
            continue

        images = []

        for node_output in task_data.get("outputs", {}).values():
            if "images" in node_output:
                images = node_output["images"]
                break
        # images = task_data["outputs"]["12"]["images"]
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



def comfy_ui_edit_run(minio_url,prompt,na_prompt,template_json,image_batch):
    name,scale = upload_input_url(minio_url)

    wf = WorkFlowInfo(template_json)
    wf.prompt = prompt
    wf.na_prompt = na_prompt
    wf.seed = get_seed()
    wf.scale = scale
    wf.image1 = name
    wf.ref_images_num = len(image_batch)



    for index, img in enumerate(image_batch):
        name1, scale = upload_input_url(img)
        if index == 0:
            wf.image2 = name1
        if index == 1:
            wf.image3 = name1
        if index == 2:
            wf.image4 = name1

    work = template_workflow_build(wf)

    logger.info("album_update work= %s", json.dumps(work, indent=4, ensure_ascii=False))
    prompt_id = comfyui_run(work)
    return prompt_id


def template_workflow_build(info:WorkFlowInfo):
    template_name = info.template_name
    files = template_dict_replace.get(template_name, None)
    if not files:
        return None

    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "work", template_name)

    template_str=None
    with open(template_path, 'r', encoding='utf-8') as f:
        template_str = f.read()

    for file in files:
        attr_name = file.strip().replace("#", "")
        value = getattr(info, attr_name, "")
        if value is None:
            value = ""
        template_str = template_str.replace(
            file,
            json.dumps(value)[1:-1]
        )

    workflow_dict = json.loads(template_str)

    if info.template_name == "qwen_edit_all_batch.json":
        num = info.ref_images_num

        # 节点ID顺序（14固定）
        optional_nodes = ["15", "16", "17"]

        # 需要删除的节点数量
        remove_count = max(0, 3 - num)

        # 从后往前删（避免逻辑错乱）
        for node_id in optional_nodes[::-1][:remove_count]:
            workflow_dict["prompt"].pop(node_id, None)

        # 同时删除 TextEncodeQwenImageEditPlus 里的引用
        text_inputs = workflow_dict["prompt"]["2"]["inputs"]

        if num < 3:
            text_inputs.pop("image4", None)
        if num < 2:
            text_inputs.pop("image3", None)
        if num < 1:
            text_inputs.pop("image2", None)

    logger.info("build_workflow workflow_dict = %s", workflow_dict)

    return workflow_dict



def comfy_ui_create_run(info:WorkFlowInfo):
    work = template_workflow_build(info)
    logger.info("build_workflow work= %s", json.dumps(work, indent=4, ensure_ascii=False))
    prompt_id = comfyui_run(work)
    return prompt_id








