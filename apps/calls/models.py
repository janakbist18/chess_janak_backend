from django.db import models
from django.utils import timezone
from apps.accounts.models import User


class Call(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('rejected', 'Rejected'),
        ('missed', 'Missed'),
    ]

    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outgoing_calls')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incoming_calls')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Call from {self.caller.username} to {self.receiver.username} - {self.status}"

    def get_duration(self):
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return 0


class CallLog(models.Model):
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='call_logs_as_caller')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='call_logs_as_receiver')
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    call_type = models.CharField(max_length=20, choices=[('audio', 'Audio'), ('video', 'Video')], default='video')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Call Log: {self.caller.username} -> {self.receiver.username}"
