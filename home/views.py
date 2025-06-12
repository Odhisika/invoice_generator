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
            subtotal_amount = Decimal('0.00')
            
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
                    
                    subtotal_amount += product_total
            
            # Handle VAT calculations
            apply_vat = request.POST.get('apply_vat') == 'on'
            vat_percentage = Decimal('0.00')
            vat_amount = Decimal('0.00')
            total_amount = subtotal_amount
            
            if apply_vat:
                try:
                    vat_percentage = Decimal(request.POST.get('vat_percentage', '0'))
                    # Validate VAT percentage is within allowed range
                    if 4 <= vat_percentage <= 14:
                        vat_amount = (subtotal_amount * vat_percentage) / Decimal('100')
                        total_amount = subtotal_amount + vat_amount
                    else:
                        messages.error(request, 'VAT percentage must be between 4% and 14%.')
                        return render(request, 'home/cash_invoice.html', {'form': form})
                except (ValueError, TypeError):
                    messages.error(request, 'Invalid VAT percentage value.')
                    return render(request, 'home/cash_invoice.html', {'form': form})
            
            # Set all the calculated amounts and VAT data
            invoice.total_amount = total_amount
            
            # Save VAT fields to the database (UNCOMMENTED AND ACTIVE)
            if hasattr(invoice, 'vat_applicable'):
                invoice.vat_applicable = apply_vat
            if hasattr(invoice, 'vat_percentage'):
                invoice.vat_percentage = vat_percentage
            if hasattr(invoice, 'vat_amount'):
                invoice.vat_amount = vat_amount
            if hasattr(invoice, 'subtotal_amount'):
                invoice.subtotal_amount = subtotal_amount
            
            # Save the invoice with all data
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
            
            # Prepare data for template display
            invoice_data = {
                'invoice_number': invoice.invoice_number,
                'customer_name': invoice.customer_name,
                'date': invoice.date,
                'customer_address': invoice.customer_address,
                'subtotal_amount': round(subtotal_amount, 2),
                'vat_applicable': apply_vat,
                'vat_percentage': round(vat_percentage, 2),
                'vat_amount': round(vat_amount, 2),
                'total_amount': round(total_amount, 2),
                'customer_sign': invoice.customer_sign,
                'manager_sign': invoice.manager_sign,
                'products': products_data
            }
            
            success_message = f'Cash Invoice {invoice.invoice_number} has been generated successfully!'
            if apply_vat:
                success_message += f' (VAT {vat_percentage}% included: GH₵{vat_amount:.2f})'
            
            messages.success(request, success_message)
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


from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

def invoice_detail(request, invoice_id):
    try:
        # Use get_object_or_404 for better error handling
        invoice = get_object_or_404(CashInvoice, id=invoice_id)
        
        # Get all products for this invoice
        products = InvoiceProduct.objects.filter(invoice=invoice)
        
        # Prepare products data - exactly like cash_invoice view
        products_data = []
        subtotal_amount = Decimal('0.00')
        
        for product in products:
            product_total = product.total
            subtotal_amount += product_total
            
            products_data.append({
                'desc': product.product_description,
                'qty': product.quantity,
                'price': product.unit_price,
                'total': product.total
            })
        
        # Handle VAT calculations - Use the exact same logic as cash_invoice view
        vat_applicable = getattr(invoice, 'vat_applicable', False)
        vat_percentage = getattr(invoice, 'vat_percentage', Decimal('0.00'))
        vat_amount = getattr(invoice, 'vat_amount', Decimal('0.00'))
        stored_subtotal = getattr(invoice, 'subtotal_amount', Decimal('0.00'))
        
        # Convert to Decimal for consistent calculations
        vat_percentage = Decimal(str(vat_percentage)) if vat_percentage else Decimal('0.00')
        vat_amount = Decimal(str(vat_amount)) if vat_amount else Decimal('0.00')
        stored_subtotal = Decimal(str(stored_subtotal)) if stored_subtotal else Decimal('0.00')
        total_amount = Decimal(str(invoice.total_amount)) if invoice.total_amount else Decimal('0.00')
        
        # Use stored subtotal if available, otherwise use calculated subtotal
        final_subtotal = stored_subtotal if stored_subtotal > 0 else subtotal_amount
        
        # Recalculate VAT and total based on stored data
        if vat_applicable and vat_percentage > 0:
            # Use stored VAT amount if available, otherwise recalculate
            if vat_amount > 0:
                final_vat = vat_amount
                final_total = total_amount
            else:
                final_vat = (final_subtotal * vat_percentage) / Decimal('100')
                final_total = final_subtotal + final_vat
        else:
            final_vat = Decimal('0.00')
            final_total = final_subtotal
            vat_percentage = Decimal('0.00')
            vat_applicable = False
        
        # Prepare invoice data for template - using EXACT same structure as cash_invoice
        invoice_data = {
            'invoice_number': invoice.invoice_number,
            'customer_name': invoice.customer_name,
            'date': invoice.date,
            'customer_address': invoice.customer_address,
            'subtotal_amount': round(final_subtotal, 2),
            'vat_applicable': vat_applicable,
            'vat_percentage': round(vat_percentage, 2),
            'vat_amount': round(final_vat, 2),
            'total_amount': round(final_total, 2),
            'customer_sign': invoice.customer_sign,
            'manager_sign': invoice.manager_sign,
            'products': products_data
        }
        
        return render(request, 'home/invoice_detail.html', {
            'invoice_data': invoice_data
        })
        
    except CashInvoice.DoesNotExist:
        messages.error(request, 'Invoice not found.')
        return redirect('home:invoice_list')
    except Exception as e:
        # More detailed error logging
        print(f"Error in invoice_detail view: {str(e)}")
        print(f"Invoice ID: {invoice_id}")
        messages.error(request, f'Error loading invoice: {str(e)}')
        return redirect('home:invoice_list')

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





