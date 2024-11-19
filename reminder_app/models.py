import calendar
import zoneinfo
import json
from django.db import models
from django_celery_beat.models import CrontabSchedule, IntervalSchedule
from django_celery_beat.models import PeriodicTask
from django_lifecycle import hook,AFTER_CREATE
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
    

    def get_schedule(self):
        if self.repeat == 'daily':
            # Default to all days if not specified
            days = self.days_of_week or '0,1,2,3,4,5,6'
            return CrontabSchedule.objects.get_or_create(
                minute=self.minute,
                hour=self.hour,
                day_of_week=days,
                timezone=TIMEZONE
            )
        elif self.repeat == 'weekly':
            if not self.days_of_week:
                raise ValueError("Days of week must be provided for weekly recurrence")
            return CrontabSchedule.objects.get_or_create(
                minute=self.minute,
                hour=self.hour,
                day_of_week=self.days_of_week,
                timezone=TIMEZONE
            )
        elif self.repeat == 'monthly':
            day_of_month = self.day_of_month or 1
            return CrontabSchedule.objects.get_or_create(
                minute=self.minute,
                hour=self.hour,
                day_of_month=day_of_month,
                timezone=TIMEZONE
            )
        elif self.repeat == 'yearly':
            if not self.day_of_month or not self.month_of_year:
                raise ValueError("Both day of month and month of year must be provided for yearly recurrence")
            return CrontabSchedule.objects.get_or_create(
                minute=self.minute,
                hour=self.hour,
                day_of_month=self.day_of_month,
                month_of_year=self.month_of_year,
                timezone=TIMEZONE
            )
        elif self.repeat_type == 'interval':
            return IntervalSchedule.objects.get_or_create(
                every=self.interval,
                period=IntervalSchedule.HOURS,
            )

        return None
    





class Medicine(models.Model):
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255)
    recurrence = models.ForeignKey(Recurrence, on_delete=models.CASCADE, blank=True, null=True)


    def __str__(self):
        return f"{self.name} - {self.dosage}"

    @hook(AFTER_CREATE)
    def schedule_task(self):
        if not self.recurrence or self.recurrence.repeat == 'none':
            PeriodicTask.objects.filter(name=f'medicine-{self.id}').delete()
            return

        schedule, _ = self.recurrence.get_schedule()
        PeriodicTask.objects.update_or_create(
            name=f'medicine-{self.id}',
            defaults={
                'task': 'reminder.tasks.send_medicine_reminder',
                'crontab': schedule,
                'enabled': True,
                'args': json.dumps([self.id]),
            }
        )