import json

from django.db import models


class BaseModel(models.Model):
    class Meta:
        abstract = True

    def __str__(self):
        data = {}
        for field in self._meta.fields:
            data[field.name] = getattr(self, field.name)
        return json.dumps(data, ensure_ascii=False)

    def to_dict(self, fields=None, exclude=None):
        """
        Model 转 dict
        :param fields: 只返回指定字段
        :param exclude: 排除字段
        """
        data = {}
        for field in self._meta.fields:
            name = field.name

            if fields and name not in fields:
                continue
            if exclude and name in exclude:
                continue

            value = getattr(self, name)
            data[name] = value
        return data


