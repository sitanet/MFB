"""
URL configuration for chart_of_account project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# chartofaccounts_project/urls.py
from django.contrib import admin
from django.urls import path, include

from profit_solutions import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # api
    path('api/v1/', include('api.urls')),  # include api app routes
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # login
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        # end api

    path('accounts_admin/', include('accounts_admin.urls')),
    path('company/', include('company.urls')),
    path('accounts/', include('accounts.urls')),
    path('customers/', include('customers.urls')),
    path('transactions/', include('transactions.urls')),
    path('end_of_periods/', include('end_of_periods.urls')),
    path('loans/', include('loans.urls')),
    path('reports/', include('reports.urls')),
    path('fixed_assets/', include('fixed_assets.urls')),
    path('fixed_deposit/', include('fixed_deposit.urls')),
    # path('audit/', include('audit_trail.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
