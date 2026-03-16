"""
Initial setup script to configure the chess backend
Run: python setup_initial.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import User as ChessUser, UserProfile
from apps.accounts.models_preferences import UserPreferences, SoundSettings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission

def create_permissions():
    """Create custom permissions for chess game"""
    print("Creating custom permissions...")
    
    permissions = [
        ('can_create_game', 'Can create chess game'),
        ('can_send_invitation', 'Can send game invitation'),
        ('can_start_video_call', 'Can start video call'),
    ]
    
    for codename, name in permissions:
        try:
            content_type = ContentType.objects.get(app_label='chessplay', model='chessmatch')
            Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={'name': name}
            )
            print(f"✓ Created permission: {codename}")
        except Exception as e:
            print(f"⚠ Error creating {codename}: {e}")

def create_test_users():
    """Create test users for development"""
    print("\nCreating test users...")
    
    test_users = [
        {'email': 'player1@example.com', 'username': 'player1', 'name': 'Player One'},
        {'email': 'player2@example.com', 'username': 'player2', 'name': 'Player Two'},
        {'email': 'ai_player@example.com', 'username': 'ai_player', 'name': 'AI Player'},
    ]
    
    for user_data in test_users:
        try:
            user, created = ChessUser.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'username': user_data['username'],
                    'name': user_data['name'],
                    'is_verified': True,
                }
            )
            if created:
                print(f"✓ Created user: {user.username}")
                # Create profile
                UserProfile.objects.get_or_create(user=user)
                # Create preferences
                UserPreferences.objects.get_or_create(user=user)
                SoundSettings.objects.get_or_create(user=user)
            else:
                print(f"⚠ User already exists: {user.username}")
        except Exception as e:
            print(f"✗ Error creating user {user_data['username']}: {e}")

def setup_email_config():
    """Setup email configuration guide"""
    print("\n" + "="*50)
    print("EMAIL CONFIGURATION REQUIRED")
    print("="*50)
    print("\nTo enable OTP-based authentication, configure these in .env:")
    print("- EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
    print("- EMAIL_HOST=smtp.gmail.com")
    print("- EMAIL_PORT=587")
    print("- EMAIL_USE_TLS=True")
    print("- EMAIL_HOST_USER=your-email@gmail.com")
    print("- EMAIL_HOST_PASSWORD=your-app-specific-password")
    print("- DEFAULT_FROM_EMAIL=your-email@gmail.com")
    print("\nFor Gmail:")
    print("1. Enable 2-factor authentication")
    print("2. Generate app-specific password")
    print("3. Use that password in EMAIL_HOST_PASSWORD")

def setup_redis_config():
    """Setup Redis configuration guide"""
    print("\n" + "="*50)
    print("REDIS CONFIGURATION FOR WEBSOCKETS")
    print("="*50)
    print("\nFor production WebSocket support, install Redis:")
    print("- Windows: Download from https://github.com/microsoftarchive/redis")
    print("- Linux: sudo apt-get install redis-server")
    print("- macOS: brew install redis")
    print("\nThen configure in settings/base.py:")
    print("""
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    }
}
""")

def display_next_steps():
    """Display next steps"""
    print("\n" + "="*50)
    print("NEXT STEPS")
    print("="*50)
    print("""
1. INSTALL DEPENDENCIES
   pip install -r requirements.txt

2. RUN MIGRATIONS
   python manage.py makemigrations
   python manage.py migrate

3. CONFIGURE EMAIL
   - Set EMAIL_* variables in .env or settings

4. INSTALL & RUN REDIS (for WebSockets)
   - Install Redis on your system
   - Run: redis-server

5. CREATE SUPERUSER
   python manage.py createsuperuser

6. RUN DEVELOPMENT SERVER
   python manage.py runserver

7. TEST OTP ENDPOINT
   POST /api/v1/accounts/auth/send_otp/
   {
       "email": "player1@example.com",
       "purpose": "login"
   }

8. FRONTEND INTEGRATION
   - Connect Flutter app to your backend endpoints
   - Use WebSockets for real-time game updates
   - Implement video call via WebRTC

DOCUMENTATION:
See IMPLEMENTATION_GUIDE.md for detailed API documentation
""")

def main():
    """Main setup function"""
    print("\n" + "="*50)
    print("CHESS JANAK BACKEND - INITIAL SETUP")
    print("="*50 + "\n")
    
    try:
        create_permissions()
        create_test_users()
        setup_email_config()
        setup_redis_config()
        display_next_steps()
        
        print("\n✅ Setup initialization complete!")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
