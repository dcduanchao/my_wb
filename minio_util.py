# utils/minio_client.py
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import requests
from django.conf import settings  # 从 Django settings 读取配置

class MinioClient:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )

    def ensure_bucket(self, bucket_name):
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def upload_file(self, bucket_name, file_path, object_name, content_type=None):
        self.ensure_bucket(bucket_name)
        try:
            self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type
            )
            return True, f"{object_name} 上传成功"
        except S3Error as e:
            return False, f"上传失败: {e}"

    def upload_bytes(self, bucket_name, object_name, data_bytes, content_type=None):
        self.ensure_bucket(bucket_name)
        try:
            re = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=BytesIO(data_bytes),
                length=len(data_bytes),
                content_type=content_type
            )

            endpoint=settings.MINIO_ENDPOINT
            prefix= "http://" if not settings.MINIO_SECURE else "https://"
            url = f"{prefix}{endpoint}/{bucket_name}/{object_name}"

            return True, f"{object_name} 上传成功",url
        except S3Error as e:
            return False, f"上传失败: {e}"

    def upload_bytes_io(self, bucket_name, object_name, data_bytes, content_type=None):
        self.ensure_bucket(bucket_name)
        try:
            re = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data_bytes,
                length=data_bytes.getbuffer().nbytes,
                content_type=content_type
            )

            endpoint=settings.MINIO_ENDPOINT
            prefix= "http://" if not settings.MINIO_SECURE else "https://"
            url = f"{prefix}{endpoint}/{bucket_name}/{object_name}"

            return True, f"{object_name} 上传成功",url
        except S3Error as e:
            return False, f"上传失败: {e}"

    def upload_from_url(self, bucket_name, object_name, url, content_type="image/jpeg"):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return self.upload_bytes(bucket_name, object_name, resp.content, content_type)
        except requests.RequestException as e:
            return False, f"下载失败: {e}"


    def delete(self, bucket_name, object_name ):
        self.ensure_bucket(bucket_name)
        try:
            self.client.remove_object(
                bucket_name=bucket_name,
                object_name=object_name
            )
            return True, f"{object_name} 删除成功"
        except S3Error as e:
            return False, f"删除失败: {e}"

# 直接暴露实例，Django 里直接 import 使用
minio_client = MinioClient()