from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chessplay.views_ads import RewardAdViewSet, UserAdRewardViewSet

router = DefaultRouter()
router.register(r'ads', RewardAdViewSet, basename='reward-ad')
router.register(r'my-rewards', UserAdRewardViewSet, basename='user-ad-reward')


class AdsIndexView(APIView):
    """Index view for ads endpoints"""
    def get(self, request):
        return Response({
            "message": "Reward Ads API",
            "endpoints": {
                "available_ads": "GET /api/chess/ads/available/",
                "all_ads": "GET /api/chess/ads/",
                "start_watching": "POST /api/chess/ads/{id}/start_watching/",
                "complete_watching": "POST /api/chess/ads/complete_watching/",
                "skip_ad": "POST /api/chess/ads/skip_ad/",
                "my_rewards": "GET /api/chess/my-rewards/",
                "completed_rewards": "GET /api/chess/my-rewards/completed/",
                "today_rewards": "GET /api/chess/my-rewards/today/",
                "reward_stats": "GET /api/chess/my-rewards/stats/",
            }
        })


urlpatterns = [
    path('', AdsIndexView.as_view(), name='ads-index'),
] + router.urls
