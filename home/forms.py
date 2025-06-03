# Updated home/forms.py
from django import forms
from datetime import date
from .models import OfficialReceipt, CashInvoice, InvoiceProduct

class OfficialReceiptForm(forms.ModelForm):
    class Meta:
        model = OfficialReceipt
        fields = [
            'date', 'received_from', 'amount', 'purpose', 'model_no',
            'cash_cheque_no', 'serial_no', 'ghc', 'manager_sign', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'purpose': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes for internal use'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = date.today()
        # Make some fields optional in the form display
        for field_name in ['model_no', 'cash_cheque_no', 'serial_no', 'ghc', 'manager_sign', 'notes']:
            self.fields[field_name].required = False

class CashInvoiceForm(forms.ModelForm):
    class Meta:
        model = CashInvoice
        fields = [
            'customer_name', 'customer_address', 'date', 
            'customer_sign', 'manager_sign', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes for internal use'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = date.today()
        # Make some fields optional
        for field_name in ['customer_address', 'customer_sign', 'manager_sign', 'notes']:
            self.fields[field_name].required = False

class InvoiceProductForm(forms.ModelForm):
    class Meta:
        model = InvoiceProduct
        fields = ['product_description', 'quantity', 'unit_price']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1, 'value': 1}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01'}),
        }





# class OfficialReceiptForm(forms.Form):
#     date = forms.DateField(initial=date.today, widget=forms.DateInput(attrs={'type': 'date'}))
#     received_from = forms.CharField(max_length=255)
#     amount = forms.DecimalField(max_digits=10, decimal_places=2)
#     purpose = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
#     model_no = forms.CharField(max_length=100, required=False)
#     cash_cheque_no = forms.CharField(max_length=100, required=False)
#     serial_no = forms.CharField(max_length=100, required=False)
#     ghc = forms.CharField(max_length=100, required=False)
#     manager_sign = forms.CharField(max_length=100, required=False)

# class CashInvoiceForm(forms.Form):
#     customer_name = forms.CharField(max_length=255)
#     date = forms.DateField(initial=date.today, widget=forms.DateInput(attrs={'type': 'date'}))
#     customer_address = forms.CharField(max_length=255, required=False)
#     total_amount = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
#     customer_sign = forms.CharField(max_length=100, required=False)
#     manager_sign = forms.CharField(max_length=100, required=False)
    
#     def __init__(self, *args, **kwargs):
#         super(CashInvoiceForm, self).__init__(*args, **kwargs)
        