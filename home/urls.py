from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'),
    path('official-receipt/', views.official_receipt, name='official_receipt'),
    path('cash-invoice/', views.cash_invoice, name='cash_invoice'),
    # List views
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    
    # Detail views
    path('receipts/<int:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    
    # Delete views
    path('receipts/<int:receipt_id>/delete/', views.delete_receipt, name='delete_receipt'),
    path('invoices/<int:invoice_id>/delete/', views.delete_invoice, name='delete_invoice'),

    # path('invoices/delete/<int:invoice_id>/', views.delete_invoice, name='delete_invoice'),
    # path('receipts/delete/<int:receipt_id>/', views.delete_receipt, name='delete_receipt'),

]