from django.urls import path
from . import views

urlpatterns = [
    path('company_list/', views.company_list, name='company_list'),
    path('branch_list/', views.branch_list, name='branch_list'),
    path('<int:pk>/', views.company_detail, name='company_detail'),
    # URL pattern for branch detail
    path('<int:pk>/branch_detail/', views.branch_detail, name='branch_detail'),
    path('create_company/', views.create_company, name='create_company'),
    path('create_branch/', views.create_branch, name='create_branch'),
    path('branch/update/<int:id>/', views.update_branch, name='update_branch'),
    path('company/session_mgt/', views.session_mgt, name='session_mgt'),
    path('<int:id>/delete/', views.company_delete, name='company_delete'),
    path('<int:id>/delete/', views.branch_delete, name='branch_delete'),
    path('session_mgt/<int:branch_id>/update/', views.session_mgt, name='session_mgt'),
]
