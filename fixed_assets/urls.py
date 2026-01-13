from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('fixed_asset_dash/', views.fixed_asset_dash, name='fixed_asset_dash'),
    
    # Asset CRUD
    path('', views.asset_list, name='asset_list'),
    path('new/', views.asset_create, name='asset_create'),
    path('asset/<uuid:uuid>/', views.asset_detail, name='asset_detail'),
    path('<uuid:uuid>/edit/', views.asset_update, name='asset_update'),
    path('<uuid:uuid>/delete/', views.asset_delete, name='asset_delete'),
    
    # Depreciation
    path('depreciation/post/<uuid:uuid>/', views.post_depreciation, name='post_depreciation'),
    path('assets/depreciate_all/', views.post_all_depreciation, name='post_all_depreciation'),
    
    # Disposal & Revaluation
    path('dispose/<uuid:uuid>/', views.dispose_fixed_asset, name='dispose_asset'),
    path('asset/<uuid:uuid>/revalue/', views.revalue_asset, name='revalue_asset'),
    
    # Asset Transfer
    path('asset/<uuid:uuid>/transfer/', views.asset_transfer, name='asset_transfer'),
    path('asset/<uuid:uuid>/transfer-history/', views.asset_transfer_history, name='asset_transfer_history'),
    
    # Asset Impairment
    path('asset/<uuid:uuid>/impairment/', views.asset_impairment, name='asset_impairment'),
    
    # Asset Insurance
    path('insurance/', views.asset_insurance_list, name='asset_insurance_list'),
    path('asset/<uuid:uuid>/insurance/add/', views.asset_insurance_add, name='asset_insurance_add'),
    
    # Asset Maintenance
    path('maintenance/', views.asset_maintenance_list, name='asset_maintenance_list'),
    path('asset/<uuid:uuid>/maintenance/add/', views.asset_maintenance_add, name='asset_maintenance_add'),
    
    # Asset Warranty
    path('warranty/', views.asset_warranty_list, name='asset_warranty_list'),
    path('asset/<uuid:uuid>/warranty/add/', views.asset_warranty_add, name='asset_warranty_add'),
    
    # Asset Verification
    path('verification/', views.asset_verification_list, name='asset_verification_list'),
    path('asset/<uuid:uuid>/verification/add/', views.asset_verification_add, name='asset_verification_add'),
    
    # Reports
    path('reports/depreciation-schedule/', views.depreciation_schedule_report, name='depreciation_schedule_report'),
    path('reports/asset-register/', views.asset_register_report, name='asset_register_report'),
    
    # Asset Type CRUD
    path('settings/types/', views.asset_type_list, name='asset_type_list'),
    path('settings/types/create/', views.asset_type_create, name='asset_type_create'),
    path('settings/types/<uuid:uuid>/edit/', views.asset_type_edit, name='asset_type_edit'),
    path('settings/types/<uuid:uuid>/delete/', views.asset_type_delete, name='asset_type_delete'),
    
    # Asset Group CRUD
    path('settings/groups/', views.asset_group_list, name='asset_group_list'),
    path('settings/groups/create/', views.asset_group_create, name='asset_group_create'),
    path('settings/groups/<uuid:uuid>/edit/', views.asset_group_edit, name='asset_group_edit'),
    
    # Asset Location CRUD
    path('settings/locations/', views.asset_location_list, name='asset_location_list'),
    path('settings/locations/create/', views.asset_location_create, name='asset_location_create'),
    path('settings/locations/<uuid:uuid>/edit/', views.asset_location_edit, name='asset_location_edit'),
    
    # Department CRUD
    path('settings/departments/', views.department_list, name='department_list'),
    path('settings/departments/create/', views.department_create, name='department_create'),
    path('settings/departments/<uuid:uuid>/edit/', views.department_edit, name='department_edit'),
    
    # Officer CRUD
    path('settings/officers/', views.officer_list, name='officer_list'),
    path('settings/officers/create/', views.officer_create, name='officer_create'),
    path('settings/officers/<uuid:uuid>/edit/', views.officer_edit, name='officer_edit'),
    
    # Depreciation Method CRUD
    path('settings/depreciation-methods/', views.depreciation_method_list, name='depreciation_method_list'),
    path('settings/depreciation-methods/create/', views.depreciation_method_create, name='depreciation_method_create'),
    path('settings/depreciation-methods/<uuid:uuid>/edit/', views.depreciation_method_edit, name='depreciation_method_edit'),
]


