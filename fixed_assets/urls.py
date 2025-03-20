from django.urls import path
from . import views
# from .views import asset_list, asset_detail, add_asset, edit_asset, dispose_asset, transfer_asset

urlpatterns = [
    path('', views.asset_list, name='asset_list'),
    path('new/', views.asset_create, name='asset_create'),
    path('<int:asset_id>/edit/', views.asset_update, name='asset_update'),
    path('<int:asset_id>/delete/', views.asset_delete, name='asset_delete'),
    path('depreciation/post/<int:asset_id>/', views.post_depreciation, name='post_depreciation'),
    path('dispose/<int:asset_id>/', views.dispose_fixed_asset, name='dispose_asset'),

    path('fixed_asset_dash/', views.fixed_asset_dash, name='fixed_asset_dash'),

    path('asset/<int:asset_id>/', views.asset_detail, name='asset_detail'),
    path("asset/<int:asset_id>/revalue/", views.revalue_asset, name="revalue_asset"),

    path('assets/depreciate_all/', views.post_all_depreciation, name='post_all_depreciation'),
]


