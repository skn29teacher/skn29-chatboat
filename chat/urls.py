from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='chat_index'),       # 메인 채팅 웹 UI 화면
    path('api/chat/', views.chat_view, name='chat_view'), # AI 추론 API 엔드포인트
]