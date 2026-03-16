"""
Authentication URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.accounts.views_auth import AuthViewSet, UserPreferencesViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'preferences', UserPreferencesViewSet, basename='preferences')

urlpatterns = [
    path('', include(router.urls)),
]
