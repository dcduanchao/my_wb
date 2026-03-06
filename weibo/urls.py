from django.urls import path

from weibo import views, test_views, comfyui_views, grok_views

app_name = 'my_weibo'
urlpatterns = [
    path('', views.index, name='index'),
    path('crawl', views.crawl, name='crawl'),
    path('records', views.records, name='records'),
    path('album', views.album, name='album'),


    path('album/delete', views.album_delete, name='album_delete'),
    path('album/update', views.album_update, name='album_update'),
    path('album/update/record', views.album_update_record, name='album_update'),
    path('album/record/delete', views.album_record_delete, name='album_record_delete'),

    # comfyui
    path("comfyui/reboot", comfyui_views.reboot, name="comfyui_reboot"),
    path("comfyui/edit", comfyui_views.comfyui_edit, name="comfyui_edit"),
    path("comfyui/edit/list", comfyui_views.comfyui_edit_list, name="comfyui_edit_list"),
    path("comfyui/image/delete", comfyui_views.comfyui_image_delete, name="comfyui_image_delete"),
    path("comfyui/create", comfyui_views.comfyui_create, name="comfyui_create"),


    # grok
    path("grok/gen", grok_views.grok_gen, name="grok_gen"),
    path("grok/list", grok_views.grok_list, name="grok_list"),
    path("grok/delete", grok_views.grok_delete, name="grok_deelete"),



    # test
    path("upload/local/", test_views.upload_local_file, name="upload_local_file"),
    path("upload/url/", test_views.upload_from_url, name="upload_from_url"),
    path("upload/delete/", test_views.upload_delete, name="upload_delete"),

    path("comfui/upload_url/", test_views.comfyui_upload_url, name="comfyui_upload_url"),
]