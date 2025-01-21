# chartofaccounts/urls.py
from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    path('withdraw/<int:id>/', views.withdraw, name='withdraw'),
    path('deposit/<int:id>/', views.deposit, name='deposit'),
    path('choose_deposit/', views.choose_deposit, name='choose_deposit'),
    path('choose_withdrawal/', views.choose_withdrawal, name='choose_withdrawal'),
    path('choose_income/', views.choose_income, name='choose_income'),
    path('choose_expense/', views.choose_expense, name='choose_expense'),
    path('income/<int:id>/', views.income, name='income'),
    path('expense/<int:id>/', views.expense, name='expense'),
    path('choose_general_journal/', views.choose_general_journal, name='choose_general_journal'),
    path('general_journal/<int:id>/', views.general_journal, name='general_journal'),
    path('memtrans/', views.memtrans_list, name='memtrans_list'),
    path('memtrans/delete/<int:memtrans_id>/', views.delete_memtrans, name='delete_memtrans'),
    path('loans_list/', views.loan_list, name='loans_list'),
    path('delete_loan/<int:id>/', views.delete_loan, name='delete_loan'),
   

    path('seek_and_update/', views.seek_and_update, name='seek_and_update'),

    path('upload/', views.upload_file, name='upload_file'),
    path('preview_data/', views.preview_data, name='preview_data'),
    path('success/', TemplateView.as_view(template_name="transactions/upload_success.html"), name='upload_success'),


    # path('add-interest-rate/', views.add_interest_rate, name='add_interest_rate'),
    path('calculate-interest/', views.calculate_interest, name='calculate_interest'),
    # path('save-calculation/', views.save_calculation, name='save_calculation'),
    # path('display-calculation/', views.display_calculation, name='display_calculation'),
    path('success/', views.success, name='success'),


    path('interest-rates/', views.interest_rate_list, name='interest_rate_list'),
    
    path('interest-rates/edit/<int:pk>/', views.edit_interest_rate, name='edit_interest_rate'),
    path('interest-rates/delete/<int:pk>/', views.delete_interest_rate, name='delete_interest_rate'),
    path('get-customer-data/', views.get_customer_data, name='get_customer_data'),
   
  

]