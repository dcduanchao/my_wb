from django.db import models

from base_model import BaseModel

class ComfyuiImage(BaseModel):
    id = models.BigAutoField(primary_key=True, db_comment='主键')
    c_type = models.IntegerField(db_comment='0：生成 1：编辑')
    img_url = models.CharField(max_length=2048, blank=True, null=True, db_comment='编辑url')
    ref_url = models.TextField(blank=True, null=True, db_comment='参考图列表')
    minio_url = models.CharField(max_length=2048, blank=True, null=True, db_comment='生图完成uil')
    video_url = models.CharField(max_length=2048, blank=True, null=True, db_comment='视频url')
    prompt = models.TextField(blank=True, null=True, db_comment='正向提示词')
    na_prompt = models.CharField(max_length=2048, blank=True, null=True, db_comment='负向')
    work_flow_name = models.CharField(max_length=255, blank=True, null=True, db_comment='工作流名称')

    class Meta:
        managed = False
        db_table = 'comfyui_image'
        db_table_comment = 'comfyui 生图'
