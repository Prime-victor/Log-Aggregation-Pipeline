from rest_framework.generics import ListAPIView
from core.permissions.rbac import IsViewerOrAbove

from .models import Alert
from .serializers import AlertSerializer


class AlertListView(ListAPIView):
    permission_classes = [IsViewerOrAbove]
    serializer_class = AlertSerializer
    queryset = Alert.objects.select_related("rule").all().order_by("-created_at")
