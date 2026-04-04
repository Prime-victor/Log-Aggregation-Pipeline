"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint for load balancers / K8s probes."""
    return JsonResponse({"status": "healthy", "service": "log-intelligence-platform"})


urlpatterns = [
    path("admin/",          admin.site.urls),
    path("health/",         health_check),

    # API v1 — all app endpoints are namespaced under /api/v1/
    path("api/v1/",         include("config.api_urls")),
]