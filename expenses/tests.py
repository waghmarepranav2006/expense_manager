from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Expense
from .forms import ExpenseForm
import datetime

class ExpenseManagerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_signup_view(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'expenses/signup.html')

    def test_login_view(self):
        self.client.logout()
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'expenses/login.html')

    def test_logout_view(self):
        response = self.client.post(reverse('logout'), follow=True)
        self.assertRedirects(response, reverse('login'))
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_view_expenses(self):
        response = self.client.get(reverse('view_expenses'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'expenses/view_expenses.html')

    def test_add_expense(self):
        response = self.client.post(reverse('add_expense'), {
            'date': datetime.date.today(),
            'amount': 100,
            'category': 'Test',
            'description': 'Test expense'
        }, follow=True)
        self.assertRedirects(response, reverse('view_expenses'))
        self.assertTrue(Expense.objects.filter(user=self.user, category='Test').exists())

    def test_edit_expense(self):
        expense = Expense.objects.create(user=self.user, date=datetime.date.today(), amount=50, category='Food')
        response = self.client.post(reverse('edit_expense', args=[expense.id]), {
            'date': datetime.date.today(),
            'amount': 75,
            'category': 'Groceries',
            'description': 'Updated expense'
        }, follow=True)
        self.assertRedirects(response, reverse('view_expenses'))
        expense.refresh_from_db()
        self.assertEqual(expense.amount, 75)
        self.assertEqual(expense.category, 'Groceries')

    def test_delete_expense(self):
        expense = Expense.objects.create(user=self.user, date=datetime.date.today(), amount=50, category='Transport')
        response = self.client.post(reverse('delete_expense', args=[expense.id]), follow=True)
        self.assertRedirects(response, reverse('view_expenses'))
        self.assertFalse(Expense.objects.filter(id=expense.id).exists())

    def test_expense_form_validation(self):
        form = ExpenseForm(data={'amount': -10})
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
