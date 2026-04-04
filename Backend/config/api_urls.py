"""
Central API URL registry.
Each app owns its own router; we include them here.
This keeps each app self-contained.
"""

from django.urls import path, include

urlpatterns = [
    path("auth/",       include("apps.authentication.urls", namespace="auth")),
    path("users/",      include("apps.users.urls",          namespace="users")),
    path("logs/",       include("apps.logs.urls",           namespace="logs")),
    path("alerts/",     include("apps.alerts.urls",         namespace="alerts")),
    path("rules/",      include("apps.rules.urls",          namespace="rules")),
    path("anomalies/",  include("apps.anomalies.urls",      namespace="anomalies")),
]