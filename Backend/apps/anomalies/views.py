from rest_framework.generics import ListAPIView
from core.permissions.rbac import IsViewerOrAbove

from .models import Anomaly
from .serializers import AnomalySerializer


class AnomalyListView(ListAPIView):
    permission_classes = [IsViewerOrAbove]
    serializer_class = AnomalySerializer
    queryset = Anomaly.objects.all().order_by("-detected_at")
