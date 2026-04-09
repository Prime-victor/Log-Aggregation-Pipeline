from django.urls import path
from .views import AnomalyListView

app_name = "anomalies"

urlpatterns = [
    path("", AnomalyListView.as_view(), name="list"),
]
