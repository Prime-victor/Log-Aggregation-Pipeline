from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import UserSerializer


class UserListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("-created_at")
