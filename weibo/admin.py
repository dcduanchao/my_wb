from django.contrib import admin

from weibo.models import WbUser, WeiboImages

# Register your models here.

admin.site.register(WbUser)
admin.site.register(WeiboImages)

