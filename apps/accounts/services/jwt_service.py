"""
JWT token generation and management service
"""
from datetime import timedelta
from typing import Dict, Tuple, Optional
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from apps.accounts.models import User


class JWTService:
    """Service for managing JWT tokens"""
    
    ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
    REFRESH_TOKEN_LIFETIME = timedelta(days=7)
    
    @staticmethod
    def get_tokens_for_user(user: User) -> Dict[str, str]:
        """
        Generate access and refresh tokens for user
        Returns: {access, refresh}
        """
        refresh = RefreshToken.for_user(user)
        
        # Customize token claims
        refresh.set_exp(lifetime=JWTService.REFRESH_TOKEN_LIFETIME)
        
        access = refresh.access_token
        access.set_exp(lifetime=JWTService.ACCESS_TOKEN_LIFETIME)
        
        # Add custom claims
        access['user_id'] = user.id
        access['username'] = user.username
        access['email'] = user.email
        refresh['user_id'] = user.id
        
        return {
            'access': str(access),
            'refresh': str(refresh),
        }
    
    @staticmethod
    def verify_token(token: str) -> Tuple[bool, Dict]:
        """Verify JWT token and return claims"""
        try:
            from rest_framework_simplejwt.tokens import TokenError
            from rest_framework_simplejwt.exceptions import InvalidToken
            
            access = RefreshToken(token).access_token
            
            return True, dict(access)
        except (TokenError, InvalidToken, Exception) as e:
            return False, {"error": str(e)}
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate new access token from refresh token
        Returns: (success, new_access_token, error_message)
        """
        try:
            from rest_framework_simplejwt.tokens import TokenError
            
            refresh = RefreshToken(refresh_token)
            access = refresh.access_token
            access.set_exp(lifetime=JWTService.ACCESS_TOKEN_LIFETIME)
            
            return True, str(access), None
        except Exception as e:
            return False, None, str(e)
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[User]:
        """Extract user from JWT token"""
        try:
            success, claims = JWTService.verify_token(token)
            if success and 'user_id' in claims:
                return User.objects.get(id=claims['user_id'])
            return None
        except User.DoesNotExist:
            return None
        except Exception:
            return None
