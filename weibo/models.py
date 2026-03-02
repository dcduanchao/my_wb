from django.db import models

from base_model import BaseModel


# Create your models here.
class WbUser(BaseModel):
    id = models.BigAutoField(primary_key=True, db_comment='主键')
    uid = models.CharField(max_length=32, db_comment='uid')
    u_name = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.CharField(max_length=1024, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wb_user'


class WeiboImages(BaseModel):
    id = models.BigAutoField(primary_key=True, db_comment='自增ID')
    uid = models.CharField(max_length=32, db_comment='uid')
    pid = models.CharField(unique=True, max_length=64, db_comment='图片唯一ID')
    mid = models.CharField(max_length=32, db_comment='微博ID')
    object_id = models.CharField(max_length=64, blank=True, null=True, db_comment='资源对象ID')
    pic_type = models.CharField(max_length=32, blank=True, null=True, db_comment='pic  ,livephoto')
    video_url = models.TextField(blank=True, null=True, db_comment='livephoto视频地址')
    is_paid = models.IntegerField(blank=True, null=True, db_comment='是否付费')
    downloaded = models.IntegerField(blank=True, null=True, db_comment='是否已下载')
    download_time = models.DateTimeField(blank=True, null=True, db_comment='下载时间')
    created_at = models.DateTimeField(blank=True, null=True, db_comment='入库时间')
    minio_url = models.CharField(max_length=2048, blank=True, null=True, db_comment='minio url')
    minio_video = models.CharField(max_length=2048, blank=True, null=True, db_comment='minio video')

    class Meta:
        managed = False
        db_table = 'weibo_images'
        db_table_comment = '微博图片表'


class WeiboUpdateImage(BaseModel):
    id = models.BigAutoField(primary_key=True, db_comment='主键')
    uid = models.CharField(max_length=32, blank=True, null=True, db_comment='uid')
    update_id = models.BigIntegerField(db_comment='修改id')
    minio_url = models.CharField(max_length=2048, blank=True, null=True, db_comment='miniourl')

    class Meta:
        managed = False
        db_table = 'weibo_update_image'



