from django.db.models import Q
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    InitiateCallView,
    AnswerCallView,
    RejectCallView,
    EndCallView,
    ActiveCallView,
    CallHistoryView,
)

urlpatterns = [
    path('initiate/', InitiateCallView.as_view(), name='initiate-call'),
    path('<int:call_id>/answer/', AnswerCallView.as_view(), name='answer-call'),
    path('<int:call_id>/reject/', RejectCallView.as_view(), name='reject-call'),
    path('<int:call_id>/end/', EndCallView.as_view(), name='end-call'),
    path('active/', ActiveCallView.as_view(), name='active-call'),
    path('history/', CallHistoryView.as_view(), name='call-history'),
]
