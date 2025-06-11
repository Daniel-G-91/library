from django.db import models
# from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta

def default_return_date():
    return timezone.now() + timedelta(days=14)

class StatusDictionary(models.Model):
    status_type = models.CharField(max_length=50)
    status_code = models.IntegerField
    status_description = models.CharField(max_length=100)


class Books(models.Model):
    book_id = models.AutoField(primary_key=True)
    book_title = models.CharField(max_length=255)
    book_author = models.CharField(max_length=255)
    samples = models.IntegerField(default=1)  # Number of available copies
    book_status = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Users(models.Model):
    user_id = models.AutoField(primary_key=True)
    user_name = models.CharField(unique=True, max_length=50)
    email = models.EmailField(unique=True, max_length=100)
    password = models.CharField(max_length=255)
    user_status = models.IntegerField(default=1)  # 1 for active, 0 for inactive
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(default=lambda: timezone.datetime(9999, 12, 31, tzinfo=timezone.utc)) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Transactions(models.Model):
    STATUS_CHOICES = [
        (0, 'Returned'),
        (1, 'Borrowed'),
        (3, 'Extended'),
        (5, 'Overdue'),
    ]

    trx_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    book_id = models.ForeignKey(Books, on_delete=models.CASCADE)
    borrow_date = models.DateTimeField(default=timezone.now)  
    return_date = models.DateTimeField(default=default_return_date())  
    trx_status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    ext_count = models.IntegerField(default=0)  # Number of extensions
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(default=lambda: timezone.datetime(9999, 12, 31, tzinfo=timezone.utc))
    updated_at = models.DateTimeField(auto_now=True)

class TransactionsAudit(models.Model):
    audit_id = models.AutoField(primary_key=True)
    trx_id = models.ForeignKey(Transactions, on_delete=models.CASCADE)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    book_id = models.ForeignKey(Books, on_delete=models.CASCADE)
    borrow_date = models.DateTimeField(default=timezone.now)  
    return_date = models.DateTimeField(default=default_return_date())  
    trx_status = models.IntegerField()
    ext_count = models.IntegerField(default=0)  # Number of extensions
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(default=lambda: timezone.datetime(9999, 12, 31, tzinfo=timezone.utc))
    audit_action = models.CharField(max_length=50) 
    audit_status = models.IntegerField(default=1)  # 1 for success, 0 for failure
    audit_timestamp = models.DateTimeField(auto_now=True)

