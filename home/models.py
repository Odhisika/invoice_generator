# home/models.py
from django.db import models
from django.utils import timezone
from decimal import Decimal

class OfficialReceipt(models.Model):
    # Receipt identification
    receipt_number = models.CharField(max_length=20, unique=True, editable=False)
    date_created = models.DateTimeField(default=timezone.now)
    
    # Receipt details
    date = models.DateField()
    received_from = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()
    model_no = models.CharField(max_length=100, blank=True, null=True)
    cash_cheque_no = models.CharField(max_length=100, blank=True, null=True)
    serial_no = models.CharField(max_length=100, blank=True, null=True)
    ghc = models.CharField(max_length=100, blank=True, null=True)
    manager_sign = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional tracking fields
    created_by = models.CharField(max_length=100, default='System')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_created']
        verbose_name = 'Official Receipt'
        verbose_name_plural = 'Official Receipts'
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate receipt number (format: OR-YYYYMMDD-XXX)
            today = timezone.now().date()
            date_str = today.strftime('%Y%m%d')
            
            # Count existing receipts for today
            count = OfficialReceipt.objects.filter(
                date_created__date=today
            ).count() + 1
            
            self.receipt_number = f"OR-{date_str}-{count:03d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.received_from}"
    
    @property
    def formatted_amount(self):
        return f"GH₵ {self.amount:,.2f}"

class CashInvoice(models.Model):
    # Invoice identification
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    date_created = models.DateTimeField(default=timezone.now)
    
    # Customer details
    customer_name = models.CharField(max_length=255)
    customer_address = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField()
    
    # Invoice totals
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Signatures
    customer_sign = models.CharField(max_length=100, blank=True, null=True)
    manager_sign = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional tracking fields
    created_by = models.CharField(max_length=100, default='System')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_created']
        verbose_name = 'Cash Invoice'
        verbose_name_plural = 'Cash Invoices'
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number (format: CI-YYYYMMDD-XXX)
            today = timezone.now().date()
            date_str = today.strftime('%Y%m%d')
            
            # Count existing invoices for today
            count = CashInvoice.objects.filter(
                date_created__date=today
            ).count() + 1
            
            self.invoice_number = f"CI-{date_str}-{count:03d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer_name}"
    
    @property
    def formatted_total(self):
        return f"GH₵ {self.total_amount:,.2f}"

class InvoiceProduct(models.Model):
    invoice = models.ForeignKey(CashInvoice, on_delete=models.CASCADE, related_name='products')
    product_description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['id']
    
    def save(self, *args, **kwargs):
        # Auto-calculate total
        self.total = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product_description} - Qty: {self.quantity}"
    
    @property
    def formatted_unit_price(self):
        return f"GH₵ {self.unit_price:,.2f}"
    
    @property
    def formatted_total(self):
        return f"GH₵ {self.total:,.2f}"



