from django.http import JsonResponse


class APIResponse(JsonResponse):

    @staticmethod
    def success_msg(msg='success'):
        """成功 + 自定义消息"""
        return JsonResponse({
            "code": 200,
            "msg": msg,
            "data": None
        })

    @staticmethod
    def success_data(msg, data):
        """成功 + 自定义消息 + 数据"""
        return JsonResponse({
            "code": 200,
            "msg": msg,
            "data": data
        },json_dumps_params={'ensure_ascii': False})

    @staticmethod
    def error(msg="失败", code=400):
        """失败"""
        return JsonResponse({
            "code": code,
            "msg": msg,
            "data": None
        },)