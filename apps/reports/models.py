from django.db import models
from apps.core.models import AuditModel

class DailySavedReport(AuditModel):
    report_date = models.DateField(unique=True)
    report_id = models.CharField(max_length=60, unique=True)
    saved_by = models.CharField(max_length=100, default='admin')
    is_locked = models.BooleanField(default=True)
    report_data = models.JSONField(default=dict)

    class Meta:
        ordering = ['-report_date', '-id']

    def __str__(self):
        return f"Daily Report {self.report_date} [{self.report_id}] (Locked: {self.is_locked})"
