from django.urls import path
from .views import RuleListView

app_name = "rules"

urlpatterns = [
    path("", RuleListView.as_view(), name="list"),
]
