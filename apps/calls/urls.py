from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.calls.views import CallViewSet

router = DefaultRouter()
router.register(r'', CallViewSet, basename='call')


class CallsIndexView(APIView):
    """Index view for calls endpoints"""
    def get(self, request):
        return Response({
            "message": "Calls API",
            "endpoints": {
                "list": "GET /api/calls/",
                "initiate": "POST /api/calls/initiate/",
                "detail": "GET /api/calls/{id}/",
                "accept": "POST /api/calls/{id}/accept/",
                "decline": "POST /api/calls/{id}/decline/",
                "end": "POST /api/calls/{id}/end/",
            }
        })


urlpatterns = [
    path('', CallsIndexView.as_view(), name='calls-index'),
] + router.urls
