from django.db import models
# from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta

class Users(models.Model):
    user_id = models.AutoField(primary_key=True)
    user_name = models.CharField(unique=True, max_length=50)
    email = models.EmailField(unique=True, max_length=100)
    password = models.CharField(max_length=255)

class Books(models.Model):
    book_id = models.AutoField(primary_key=True)
    book_title = models.CharField(max_length=255)
    book_author = models.CharField(max_length=255)
    samples = models.IntegerField(default=1)  # Number of available copies
    
def default_return_date():
    return timezone.now() + timedelta(days=14)

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
    borrow_date = models.DateTimeField(default=timezone.now)  # Default = current date
    return_date = models.DateTimeField(default=default_return_date())  # Default = borrow date + 14 days
    trx_status = models.IntegerField(choices=STATUS_CHOICES, default=1)


