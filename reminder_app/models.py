import calendar
import zoneinfo
from django.db import models
from django_celery_beat.models import CrontabSchedule, IntervalSchedule

TIMEZONE = zoneinfo.ZoneInfo('Asia/Kolkata')

class Recurrence(models.Model):
    repeat_choices = [
        ('none', 'Does not repeat'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ]
    repeat = models.CharField(max_length=10, choices=repeat_choices, default='none')
    repeat_every = models.PositiveIntegerField(blank=True, null=True)
    days_of_week = models.CharField(max_length=255, blank=True, null=True)
    day_of_month = models.PositiveIntegerField(blank=True, null=True)
    month_of_year = models.PositiveIntegerField(blank=True, null=True)
    minute = models.PositiveIntegerField(default=0)
    hour = models.PositiveIntegerField(default=9)  # default: 9AM
    
    def __str__(self):
        return f"Reminder set for {self.description}"

    @property
    def description(self):
        # Return a friendly string describing the schedule
        if self.repeat == 'daily':
            return "Daily at {}:{}".format(self.hour, self.minute)
        elif self.repeat == 'weekly':
            days = self.days_of_week or 'every day'
            return "Weekly on {} at {}:{}".format(days, self.hour, self.minute)
        return "Custom schedule"