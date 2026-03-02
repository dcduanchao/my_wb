import time

from weibo.models import WeiboImages
from weibo.wbapi import get_user_uid_album

import logging

logger = logging.getLogger()



def get_image1(uid, sinceid=0):

    error_num = 0
    stop_page_count = 0      # 连续无新数据页数
    STOP_THRESHOLD = 3       # 连续3页无新数据就停止
    count = 0
    while True:
        try:
            resp = get_user_uid_album(uid, sinceid)
            if resp is None:
                logger.info("resp is null uid=%s sinceid=%s", uid, sinceid)
                break

            data = resp.json().get('data', {})

            since_id = data.get("since_id")

            if not since_id or since_id == "0":
                logger.info("since_id is null uid=%s", uid)
                break

            sinceid = since_id

            api_list = data.get("list", [])
            if not api_list:
                break

            # 取出当前页所有 pid
            pids = [item.get("pid") for item in api_list]

            # 查数据库已有 pid（一次 SQL）
            existing_pids = set(
                WeiboImages.objects.filter(pid__in=pids)
                .values_list("pid", flat=True)
            )

            images = []

            for item in api_list:
                if item.get("pid") is None:
                    continue
                if item["pid"] not in existing_pids:
                    images.append(
                        WeiboImages(
                            uid=uid,
                            pid=item.get("pid"),
                            mid=item.get("mid"),
                            object_id=item.get("object_id"),
                            pic_type=item.get("type", "pic"),
                            video_url=item.get("video"),
                            is_paid=item.get("is_paid", False),
                            downloaded=0
                        )
                    )
                    count+=1

            # 3⃣ 批量插入
            if images:
                WeiboImages.objects.bulk_create(
                    images,
                    batch_size=200
                )
                stop_page_count = 0   # 有新数据，重置
            else:
                stop_page_count += 1  # 本页无新数据

            # 4 连续3页无新数据 → 停止
            if stop_page_count >= STOP_THRESHOLD:
                logger.info("no new data, stop uid=%s", uid)
                break

            time.sleep(0.1)

        except Exception as e:
            logger.exception("get_image error uid=%s sinceid=%s", uid, sinceid)
            error_num += 1
            if error_num > 5:
                break

    logger.info("get_image stop uid=%s count=%s", uid, count)


