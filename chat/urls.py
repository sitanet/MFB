from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_home, name='chat_home'),
    path('room/<uuid:room_uuid>/', views.chat_room, name='chat_room'),
    path('start/<int:user_id>/', views.start_chat, name='start_chat'),
    path('send/', views.send_message, name='send_message'),
    path('messages/<uuid:room_uuid>/', views.get_messages, name='get_messages'),
    path('unread/', views.get_unread_count, name='get_unread_count'),
    path('search/', views.search_staff, name='search_staff'),
]
