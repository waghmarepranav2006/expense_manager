# expenses/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('delete_account/', views.delete_account_view, name='delete_account'),
    path('chart/', views.chart_view, name='chart'),
    path('export/', views.export_to_csv, name='export_to_csv'),
    path('', views.view_expenses, name='view_expenses'), # Dashboard/Home Page [cite: 76]
    path('add/', views.add_expense, name='add_expense'),
    path('edit/<int:expense_id>/', views.edit_expense, name='edit_expense'),
    path('delete/<int:expense_id>/', views.delete_expense, name='delete_expense'),
]
