from django.contrib import admin
from .models import Users, Books, Transactions

admin.site.register(Users)
admin.site.register(Books)
admin.site.register(Transactions)