# expenses/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Expense
from .forms import ExpenseForm, CustomUserCreationForm
from django.shortcuts import get_object_or_404
from django.db.models import Sum
import json


def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('view_expenses') # Redirect to dashboard after signup
    else:
        form = CustomUserCreationForm()
    return render(request, 'expenses/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('view_expenses') # Redirect to dashboard after login
    else:
        form = AuthenticationForm()
    return render(request, 'expenses/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        logout(request)
        return redirect('login')
    return render(request, 'expenses/delete_account_confirm.html')

@login_required
def chart_view(request):
    expenses = Expense.objects.filter(user=request.user)
    category_data = expenses.values('category').annotate(total=Sum('amount'))
    category_labels = [item['category'] for item in category_data]
    category_totals = [float(item['total']) for item in category_data]

    context = {
        'category_labels': json.dumps(category_labels),
        'category_totals': json.dumps(category_totals),
    }
    return render(request, 'expenses/chart.html', context)


@login_required
def view_expenses(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    categories = Expense.objects.filter(user=request.user).values_list('category', flat=True).distinct()

    # Filtering logic
    category_filter = request.GET.get('category')
    start_date_filter = request.GET.get('start_date')
    end_date_filter = request.GET.get('end_date')

    if category_filter:
        expenses = expenses.filter(category=category_filter)
    if start_date_filter:
        expenses = expenses.filter(date__gte=start_date_filter)
    if end_date_filter:
        expenses = expenses.filter(date__lte=end_date_filter)

    context = {
        'expenses': expenses,
        'categories': categories,
    }

    return render(request, 'expenses/view_expenses.html', context)


# Add Expense (REQ-4 to REQ-6) [cite: 99, 100, 102]
@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user  # Assign the logged-in user
            expense.save()
            return redirect('view_expenses')
    else:
        form = ExpenseForm()
    return render(request, 'expenses/add_edit_expense.html', {'form': form, 'title': 'Add Expense'})


# Edit Expense (REQ-11, REQ-12) [cite: 117, 119]
@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)  # Ensure user owns the expense
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('view_expenses')
    else:
        form = ExpenseForm(instance=expense)  # Pre-fills the form [cite: 118]
    return render(request, 'expenses/add_edit_expense.html', {'form': form, 'title': 'Edit Expense'})


# Delete Expense (REQ-13, REQ-14) [cite: 120, 121]
@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    if request.method == 'POST':
        expense.delete()
        return redirect('view_expenses')
    return render(request, 'expenses/delete_confirm.html', {'expense': expense})
