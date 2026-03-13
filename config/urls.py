from django.contrib import admin
from django.urls import path, include 

urlpatterns = [
    path("admin/", admin.site.urls),
    # market_api의 urls.py를 'api/' 경로로 연결
    path("api/", include("market_api.urls")), 
]