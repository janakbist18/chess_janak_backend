from django.conf import settings
from django.db import models
from django.utils import timezone


class Call(models.Model):
    """Voice/Video Call between users"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('declined', 'Declined'),
        ('missed', 'Missed'),
    ]

    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="initiated_calls"
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_calls"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    call_type = models.CharField(
        max_length=20,
        choices=[('voice', 'Voice'), ('video', 'Video')],
        default='voice'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Call"
        verbose_name_plural = "Calls"

    def __str__(self):
        return f"Call from {self.caller} to {self.receiver}"

    @property
    def duration(self):
        """Get call duration in seconds"""
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return None

    def accept(self):
        """Accept the call"""
        if self.status == 'pending':
            self.status = 'active'
            self.started_at = timezone.now()
            self.save()

    def decline(self):
        """Decline the call"""
        if self.status == 'pending':
            self.status = 'declined'
            self.ended_at = timezone.now()
            self.save()

    def end(self):
        """End the call"""
        if self.status == 'active':
            self.status = 'completed'
            self.ended_at = timezone.now()
            self.save()
