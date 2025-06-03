# Updated home/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import OfficialReceipt, CashInvoice, InvoiceProduct
from .forms import OfficialReceiptForm, CashInvoiceForm, InvoiceProductForm
from decimal import Decimal
import re
from django.views.decorators.http import require_POST

def index(request):
    # Get recent receipts and invoices for dashboard
    recent_receipts = OfficialReceipt.objects.all()[:5]
    recent_invoices = CashInvoice.objects.all()[:5]
    
    # Get some statistics
    total_receipts = OfficialReceipt.objects.count()
    total_invoices = CashInvoice.objects.count()
    
    context = {
        'recent_receipts': recent_receipts,
        'recent_invoices': recent_invoices,
        'total_receipts': total_receipts,
        'total_invoices': total_invoices,
    }
    
    return render(request, 'home/index.html', context)

def official_receipt(request):
    if request.method == 'POST':
        form = OfficialReceiptForm(request.POST)
        if form.is_valid():
            receipt = form.save()
            messages.success(request, f'Official Receipt {receipt.receipt_number} has been generated successfully!')
            return render(request, 'home/official_receipt.html', {
                'form': OfficialReceiptForm(), 
                'receipt_data': receipt
            })
    else:
        form = OfficialReceiptForm()
    
    return render(request, 'home/official_receipt.html', {'form': form})

def cash_invoice(request):
    if request.method == 'POST':
        form = CashInvoiceForm(request.POST)
        if form.is_valid():
            # Create the invoice
            invoice = form.save(commit=False)
            
            # Process product data from POST
            products_data = []
            total_amount = Decimal('0.00')
            
            product_pattern = re.compile(r'product_desc_(\d+)')
            product_rows = set()
            
            # Find all product rows
            for key in request.POST:
                match = product_pattern.match(key)
                if match:
                    product_rows.add(match.group(1))
            
            # Process each product row
            for row_num in sorted(product_rows):
                desc_key = f'product_desc_{row_num}'
                qty_key = f'product_qty_{row_num}'
                price_key = f'product_price_{row_num}'
                
                if all(key in request.POST for key in [desc_key, qty_key, price_key]):
                    desc = request.POST[desc_key]
                    qty = int(request.POST[qty_key])
                    price = Decimal(request.POST[price_key])
                    product_total = qty * price
                    
                    products_data.append({
                        'desc': desc,
                        'qty': qty,
                        'price': price,
                        'total': product_total
                    })
                    
                    total_amount += product_total
            
            # Set the calculated total
            invoice.total_amount = total_amount
            invoice.save()
            
            # Create invoice products
            for product_data in products_data:
                InvoiceProduct.objects.create(
                    invoice=invoice,
                    product_description=product_data['desc'],
                    quantity=product_data['qty'],
                    unit_price=product_data['price'],
                    total=product_data['total']
                )
            
            # Prepare data for template
            invoice_data = {
                'invoice_number': invoice.invoice_number,
                'customer_name': invoice.customer_name,
                'date': invoice.date,
                'customer_address': invoice.customer_address,
                'total_amount': invoice.total_amount,
                'customer_sign': invoice.customer_sign,
                'manager_sign': invoice.manager_sign,
                'products': products_data
            }
            
            messages.success(request, f'Cash Invoice {invoice.invoice_number} has been generated successfully!')
            return render(request, 'home/cash_invoice.html', {
                'form': CashInvoiceForm(),  
                'invoice_data': invoice_data
            })
    else:
        form = CashInvoiceForm()
    
    return render(request, 'home/cash_invoice.html', {'form': form})

def receipt_list(request):
    """View to list all official receipts"""
    receipts_list = OfficialReceipt.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        receipts_list = receipts_list.filter(
            Q(receipt_number__icontains=search_query) |
            Q(received_from__icontains=search_query) |
            Q(purpose__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(receipts_list, 10)  # Show 10 receipts per page
    page_number = request.GET.get('page')
    receipts = paginator.get_page(page_number)
    
    return render(request, 'home/receipt_list.html', {
        'receipts': receipts,
        'search_query': search_query
    })

def invoice_list(request):
    """View to list all cash invoices"""
    invoices_list = CashInvoice.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        invoices_list = invoices_list.filter(
            Q(invoice_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_address__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(invoices_list, 10)  # Show 10 invoices per page
    page_number = request.GET.get('page')
    invoices = paginator.get_page(page_number)
    
    return render(request, 'home/invoice_list.html', {
        'invoices': invoices,
        'search_query': search_query
    })

def receipt_detail(request, receipt_id):
    """View to display a specific receipt"""
    receipt = get_object_or_404(OfficialReceipt, id=receipt_id)
    return render(request, 'home/receipt_detail.html', {'receipt': receipt})

# def invoice_detail(request, invoice_id):
#     """View to display a specific invoice"""
#     invoice = get_object_or_404(CashInvoice, id=invoice_id)
#     return render(request, 'home/invoice_detail.html', {'invoice': invoice})


def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(CashInvoice, pk=invoice_id)
    
    # Get all products for this invoice
    invoice_products = InvoiceProduct.objects.filter(invoice=invoice)
    
    # Format products data to match template expectations
    products_data = []
    for product in invoice_products:
        products_data.append({
            'desc': product.product_description,
            'qty': product.quantity,
            'price': product.unit_price,
            'total': product.total
        })
    
    invoice_data = {
        "invoice_number": invoice.invoice_number,
        "customer_name": invoice.customer_name,
        "customer_address": invoice.customer_address,
        "date": invoice.date,
        "total_amount": invoice.formatted_total,
        "customer_sign": invoice.customer_sign,
        "manager_sign": invoice.manager_sign,
        "notes": invoice.notes,
        "created_by": invoice.created_by,
        "date_created": invoice.date_created,
        "products": products_data  # This was missing!
    }
    
    return render(request, "home/invoice_detail.html", {"invoice_data": invoice_data})

@require_POST
def delete_receipt(request, receipt_id):
   
    receipt = get_object_or_404(OfficialReceipt, id=receipt_id)
    receipt_number = receipt.receipt_number
    receipt.delete()
    messages.success(request, f'receipt {receipt_number} has been deleted successfully!')
    return redirect('home:receipt_list')



@require_POST
def delete_invoice(request, invoice_id):
   
    invoice = get_object_or_404(CashInvoice, id=invoice_id)
    invoice_number = invoice.invoice_number
    invoice.delete()
    messages.success(request, f'Invoice {invoice_number} has been deleted successfully!')
    return redirect('home:invoice_list')





