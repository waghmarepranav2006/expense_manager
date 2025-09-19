from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'category', 'amount')
    list_filter = ('user', 'category', 'date')
    search_fields = ('description', 'category')
