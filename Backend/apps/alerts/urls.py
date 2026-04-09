from django.urls import path
from .views import AlertListView

app_name = "alerts"

urlpatterns = [
    path("", AlertListView.as_view(), name="list"),
]
