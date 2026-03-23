"""
Stripe payment API serializers.
Handles request/response validation for payment endpoints.
"""
from rest_framework import serializers
from django.conf import settings
from .models import PaymentPackageStripe, StripePaymentIntent


class PaymentPackageSerializer(serializers.ModelSerializer):
    """Serialize coin package details for client."""
    value_per_coin = serializers.SerializerMethodField()

    class Meta:
        model = PaymentPackageStripe
        fields = [
            'id', 'name', 'coins', 'price_usd', 'price_eur', 'price_gbp',
            'discount_percentage', 'is_popular', 'value_per_coin', 'is_active'
        ]
        read_only_fields = fields

    def get_value_per_coin(self, obj):
        """Calculate value per coin based on USD."""
        if obj.coins > 0:
            return round(float(obj.price_usd) / obj.coins, 4)
        return 0


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Validate payment intent creation request."""
    package_id = serializers.IntegerField(required=True, min_value=1)
    currency = serializers.ChoiceField(
        choices=['usd', 'eur', 'gbp'],
        default='usd',
        required=False
    )

    def validate_package_id(self, value):
        """Verify package exists and is active."""
        if not PaymentPackageStripe.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive package")
        return value


class PaymentIntentResponseSerializer(serializers.Serializer):
    """Return payment intent details to client."""
    client_secret = serializers.CharField()
    payment_intent_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_cents = serializers.IntegerField()
    currency = serializers.CharField()
    package_id = serializers.IntegerField()
    coins = serializers.IntegerField()
    discount_percentage = serializers.IntegerField()


class PaymentStatusSerializer(serializers.Serializer):
    """Return payment status to client."""
    status = serializers.CharField()
    coins = serializers.IntegerField()
    amount = serializers.CharField()
    currency = serializers.CharField()


class ListPackagesSerializer(serializers.Serializer):
    """Validate list packages request."""
    currency = serializers.ChoiceField(
        choices=['usd', 'eur', 'gbp'],
        default='usd',
        required=False
    )


class PackageListResponseSerializer(serializers.Serializer):
    """Return package list."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    coins = serializers.IntegerField()
    price = serializers.CharField()
    currency = serializers.CharField()
    discount_percentage = serializers.IntegerField()
    is_popular = serializers.BooleanField()
    value_per_coin = serializers.CharField()
