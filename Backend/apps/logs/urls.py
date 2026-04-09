from django.urls import path
from .views import LogSearchView, LogAggregationsView, LogTraceView

app_name = "logs"

urlpatterns = [
    path("search/", LogSearchView.as_view(), name="search"),
    path("aggregations/", LogAggregationsView.as_view(), name="aggregations"),
    path("trace/<str:trace_id>/", LogTraceView.as_view(), name="trace"),
]
