# expenses/models.py
from django.db import models
from django.contrib.auth.models import User


# Model to store expense data
class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Entertainment', 'Entertainment'),
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Bills', 'Bills'),
        ('Healthcare', 'Healthcare'),
        ('Other', 'Other'),
    ]

    # Link each expense to a specific user. This fulfills REQ-3.
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Expense details as per REQ-4
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Using DecimalField is best practice for currency
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, null=True)  # Optional description

    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.amount}"
