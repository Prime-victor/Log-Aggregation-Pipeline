from rest_framework.generics import ListAPIView
from core.permissions.rbac import IsViewerOrAbove

from .models import Rule
from .serializers_api import RuleSerializer


class RuleListView(ListAPIView):
    permission_classes = [IsViewerOrAbove]
    serializer_class = RuleSerializer
    queryset = Rule.objects.select_related("created_by").all().order_by("-created_at")
