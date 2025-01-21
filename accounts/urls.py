from django.urls import path
from . import views



urlpatterns = [
   
    path('myAccount/', views.myAccount, name='myAccount'),
    path('registeruser/', views.registeruser, name='registeruser'),
    path('registerusermasterintelligent/', views.registerusermasterintelligent, name='registerusermasterintelligent'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('change_password/', views.change_password, name='change_password'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
   
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('reset_password_validate/<uidb64>/<token>/', views.reset_password_validate, name='reset_password_validate'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('change_password/', views.change_password, name='change_password'),
    path('user_admin/', views.user_admin, name='user_admin'),
    path('display_all_user/', views.display_all_user, name='display_all_user'),
    path('edit_user/<int:id>/', views.edit_user, name='edit_user'),
    path('delete_user/<int:id>/', views.delete_user, name='delete_user'),
 
    
]