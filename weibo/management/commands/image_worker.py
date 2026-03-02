import logging
import time
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from io import BytesIO

import requests
from django.core.management.base import BaseCommand

from minio_util import minio_client
from weibo import wb_header
from weibo.models import WeiboImages


logger = logging.getLogger(__name__)

MAX_WORKERS = 10
BATCH_SIZE = 1000

headers = wb_header.headers


class Command(BaseCommand):
    help = "上传未下载图片到 MinIO"

    def handle(self, *args, **options):
        executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

        try:
            while True:
                print("Worker started")
                # down = WeiboImages.objects.filter(downloaded=0).order_by('id')[:1000]

                down = list(
                    WeiboImages.objects
                    .filter(downloaded=0)
                    .order_by('id')[:BATCH_SIZE]
                )
                if len(down) == 0:
                    time.sleep(60)
                    continue
                # with 退出不了
                # with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                #     futures = [executor.submit(self.process_image, wimage) for wimage in down]
                #
                #     # 等待这一批全部完成
                #     for future in as_completed(futures):
                #         try:
                #             future.result()
                #         except Exception as e:
                #             logger.exception("线程执行异常: %s", e)

                futures = [
                    executor.submit(self.process_image, wimage)
                    for wimage in down
                ]

                for future in as_completed(futures):
                    future.result()

                print(f"本批 {len(down)} 条处理完成")

                time.sleep(1)
        except KeyboardInterrupt:
            print("收到 Ctrl+C，正在优雅退出...")
            executor.shutdown(wait=False, cancel_futures=True)
            return

    def process_image(self,wimage: WeiboImages):
            try:
                pid = wimage.pid
                type = wimage.pic_type
                filename=f'{pid}.jpg'
                #orj360
                im_url =f'https://wx3.sinaimg.cn/large/{pid}.jpg'
                response = requests.get(im_url,headers=headers,timeout=30)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type")
                re = minio_client.upload_bytes("weibo", filename, response.content, content_type)
                status_code, msg, url = re
                wimage.minio_url = url
                wimage.downloaded=1

                if type == 'livephoto':
                   video =  wimage.video_url
                   # 下载视频（流式）
                   response = requests.get(video, headers=headers, timeout=60, stream=True)
                   response.raise_for_status()

                   video_data = BytesIO()
                   for chunk in response.iter_content(chunk_size=8192):
                       if chunk:
                           video_data.write(chunk)
                   video_data.seek(0)  # 重置指针

                   # 设置 content_type 根据后缀
                   if video.endswith("mov"):
                       content_type = "video/quicktime"  # mov 文件
                       object_name = f"{pid}.mov"
                   else:
                       content_type = "image/mp4"
                       object_name = f"{pid}.mp4"
                   re = minio_client.upload_bytes_io("weibo", object_name, video_data, content_type)
                   status_code, msg, v_url = re
                   wimage.minio_video = v_url

                wimage.save(update_fields=["minio_url", "downloaded","minio_video"])
                logger.info("minio wimage id=%s 完成",wimage.id)
            except:
                logger.exception("process_image error pid=%s", pid)




