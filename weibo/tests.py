import json
import random
from io import BytesIO


from PIL import Image
from io import BytesIO
import requests


from weibo.comfyui.comfui_api import build_comfyui_prompt, upload_input_url, comfyui_run, comfyui_history

def test2():
    url = "http://192.168.30.33:9100/weibo/006eVYYigy1hgqxdkmxizj32c0340e83.jpg"
    upload_image_name ,scale= upload_input_url(url)

    prompt_text = "移除图1中衣服"
    work = build_comfyui_prompt(prompt_text, upload_image_name,scale)
    print(json.dumps(work, indent=4, ensure_ascii=False))
    prompt_id = comfyui_run(work)
    print(prompt_id)

    if prompt_id is None:
        print("error")

    img = comfyui_history(prompt_id)
    print(img)

def test1():


    url="http://192.168.30.33:9100/weibo/006eVYYigy1ia1a6piaq4j32yo3y8x70.jpg"
    # 1. 下载原图
    resp = requests.get(url)
    resp.raise_for_status()
    image_bytes = BytesIO(resp.content)
    img = Image.open(image_bytes)

    MAX_WIDTH, MAX_HEIGHT = 1024, 1024
    # 2. 获取原图大小
    w, h = img.size

    print(w, h)

    # 3. 根据最大尺寸计算缩放比例（等比缩放）
    scale_w = MAX_WIDTH / w
    scale_h = MAX_HEIGHT / h
    scale = min(scale_w, scale_h, 1.0)  # 不放大，只缩小

    print(f"原图: {w}x{h}, scale_by = {scale:.1f}")

if __name__ == '__main__':
    test1()






