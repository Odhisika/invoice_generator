# Updated home/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from .models import OfficialReceipt, CashInvoice, InvoiceProduct
from .forms import OfficialReceiptForm, CashInvoiceForm, InvoiceProductForm
from decimal import Decimal
import re
from django.views.decorators.http import require_POST

def index(request):
    recent_receipts = OfficialReceipt.objects.all()[:5]
    recent_invoices = CashInvoice.objects.filter(status='FINAL')[:5]

    receipt_stats = OfficialReceipt.objects.aggregate(
        total_revenue=Sum('amount')
    )
    invoice_stats = CashInvoice.objects.filter(status='FINAL').aggregate(
        total_revenue=Sum('total_amount')
    )

    context = {
        'recent_receipts': recent_receipts,
        'recent_invoices': recent_invoices,
        'total_receipts': OfficialReceipt.objects.count(),
        'total_receipt_revenue': receipt_stats['total_revenue'] or 0,
        'total_invoices': CashInvoice.objects.filter(status='FINAL').count(),
        'total_invoice_revenue': invoice_stats['total_revenue'] or 0,
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
            
            # Handle VAT calculations (ONLY on products)
            apply_vat = request.POST.get('apply_vat') == 'on'
            vat_percentage = Decimal('0.00')
            vat_amount = Decimal('0.00')
            total_amount = subtotal_amount
            
            if apply_vat:
                try:
                    vat_percentage = Decimal(request.POST.get('vat_percentage', '0'))
                    # Validate VAT percentage is within allowed range
                    if 4 <= vat_percentage <= 22:
                        vat_amount = (subtotal_amount * vat_percentage) / Decimal('100')
                        total_amount = subtotal_amount + vat_amount
                    else:
                        messages.error(request, 'VAT percentage must be between 4% and 22%.')
                        return render(request, 'home/cash_invoice.html', {'form': form})
                except (ValueError, TypeError):
                    messages.error(request, 'Invalid VAT percentage value.')
                    return render(request, 'home/cash_invoice.html', {'form': form})
            
            
            # Process non-tax items (transport/delivery) - NOT affected by VAT
            nontax_data = []
            nontax_total = Decimal('0.00')
            
            nontax_pattern = re.compile(r'nontax_desc_(\d+)')
            nontax_rows = set()
            
            # Find all non-tax rows
            for key in request.POST:
                match = nontax_pattern.match(key)
                if match:
                    nontax_rows.add(match.group(1))
            
            # Process each non-tax row
            for row_num in sorted(nontax_rows):
                desc_key = f'nontax_desc_{row_num}'
                qty_key = f'nontax_qty_{row_num}'
                price_key = f'nontax_price_{row_num}'
                
                # Only process if all fields are present and description is not empty
                if all(key in request.POST for key in [desc_key, qty_key, price_key]):
                    desc = request.POST[desc_key].strip()
                    if desc:  # Only add if description is not empty
                        try:
                            qty = int(request.POST[qty_key])
                            price = Decimal(request.POST[price_key])
                            nontax_item_total = qty * price
                            
                            nontax_data.append({
                                'desc': desc,
                                'qty': qty,
                                'price': price,
                                'total': nontax_item_total
                            })
                            
                            nontax_total += nontax_item_total
                        except (ValueError, TypeError):
                            pass  # Skip invalid entries
            
            # Add non-tax total to final amount (after VAT, not affected by VAT)
            total_amount += nontax_total
            
            # Set all the calculated amounts and VAT data
            invoice.total_amount = total_amount
            
            # Save VAT fields to the database
            if hasattr(invoice, 'vat_applicable'):
                invoice.vat_applicable = apply_vat
            if hasattr(invoice, 'vat_percentage'):
                invoice.vat_percentage = vat_percentage
            if hasattr(invoice, 'vat_amount'):
                invoice.vat_amount = vat_amount
            if hasattr(invoice, 'subtotal_amount'):
                invoice.subtotal_amount = subtotal_amount
            if hasattr(invoice, 'nontax_total'):
                invoice.nontax_total = nontax_total
            
            invoice.status = 'FINAL'
            invoice.save()
            
            # Create invoice products
            # Create invoice products (Taxable)
            for product_data in products_data:
                InvoiceProduct.objects.create(
                    invoice=invoice,
                    product_description=product_data['desc'],
                    quantity=product_data['qty'],
                    unit_price=product_data['price'],
                    total=product_data['total'],
                    is_taxable=True
                )
            
            # Create invoice products (Non-Taxable)
            for nontax_item in nontax_data:
                InvoiceProduct.objects.create(
                    invoice=invoice,
                    product_description=nontax_item['desc'],
                    quantity=nontax_item['qty'],
                    unit_price=nontax_item['price'],
                    total=nontax_item['total'],
                    is_taxable=False
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
                'nontax_items': nontax_data,
                'nontax_total': round(nontax_total, 2),
                'total_amount': round(total_amount, 2),
                'customer_sign': invoice.customer_sign,
                'manager_sign': invoice.manager_sign,
                'products': products_data
            }
            
            success_message = f'Cash Invoice {invoice.invoice_number} has been generated successfully!'
            if apply_vat:
                success_message += f' (VAT {vat_percentage}% included: GH₵{vat_amount:.2f})'
            if nontax_total > 0:
                success_message += f' + Non-Tax Items: GH₵{nontax_total:.2f}'
            
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

def edit_invoice(request, invoice_id):
    invoice = get_object_or_404(CashInvoice, id=invoice_id)
    
    # Session-based authorization for editing FINAL invoices
    auth_key = f'invoice_edit_{invoice_id}'
    is_authorized = request.session.get(auth_key, False)
    
    # Handle password verification POST (from modal)
    if request.method == 'POST' and request.POST.get('authorize') == '1':
        password = request.POST.get('edit_password', '')
        if request.user.check_password(password):
            request.session[auth_key] = True
            messages.success(request, 'Password verified. You can now edit this finalized invoice.')
            return redirect('home:edit_invoice', invoice_id=invoice_id)
        else:
            messages.error(request, 'Incorrect password.')
            return redirect('home:edit_invoice', invoice_id=invoice_id)
    
    if request.method == 'POST':
        # Block unauthorized edit of FINAL invoices
        if invoice.status == 'FINAL' and not is_authorized:
            messages.error(request, 'You must authorize with your password to edit a finalized invoice.')
            return redirect('home:edit_invoice', invoice_id=invoice_id)
        
        form = CashInvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            invoice = form.save(commit=False)
            
            # Process product data from POST
            products_data = []
            subtotal_amount = Decimal('0.00')
            product_pattern = re.compile(r'product_desc_(\d+)')
            product_rows = set()
            for key in request.POST:
                match = product_pattern.match(key)
                if match:
                    product_rows.add(match.group(1))
            
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
                        'desc': desc, 'qty': qty, 'price': price, 'total': product_total
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
                    if 4 <= vat_percentage <= 22:
                        vat_amount = (subtotal_amount * vat_percentage) / Decimal('100')
                        total_amount = subtotal_amount + vat_amount
                    else:
                        messages.error(request, 'VAT percentage must be between 4% and 22%.')
                        taxable_products = invoice.products.filter(is_taxable=True)
                        nontax_items = invoice.products.filter(is_taxable=False)
                        return render(request, 'home/cash_invoice.html', {
                            'form': form, 'edit_mode': True, 'invoice': invoice,
                            'taxable_products': taxable_products, 'nontax_items': nontax_items,
                            'require_password': False, 'password_verified': True,
                        })
                except (ValueError, TypeError):
                    messages.error(request, 'Invalid VAT percentage value.')
                    taxable_products = invoice.products.filter(is_taxable=True)
                    nontax_items = invoice.products.filter(is_taxable=False)
                    return render(request, 'home/cash_invoice.html', {
                        'form': form, 'edit_mode': True, 'invoice': invoice,
                        'taxable_products': taxable_products, 'nontax_items': nontax_items,
                        'require_password': False, 'password_verified': True,
                    })
            
            # Process non-tax items
            nontax_data = []
            nontax_total = Decimal('0.00')
            nontax_pattern = re.compile(r'nontax_desc_(\d+)')
            nontax_rows = set()
            for key in request.POST:
                match = nontax_pattern.match(key)
                if match:
                    nontax_rows.add(match.group(1))
            
            for row_num in sorted(nontax_rows):
                desc_key = f'nontax_desc_{row_num}'
                qty_key = f'nontax_qty_{row_num}'
                price_key = f'nontax_price_{row_num}'
                if all(key in request.POST for key in [desc_key, qty_key, price_key]):
                    desc = request.POST[desc_key].strip()
                    if desc:
                        try:
                            qty = int(request.POST[qty_key])
                            price = Decimal(request.POST[price_key])
                            nontax_item_total = qty * price
                            nontax_data.append({
                                'desc': desc, 'qty': qty, 'price': price, 'total': nontax_item_total
                            })
                            nontax_total += nontax_item_total
                        except (ValueError, TypeError):
                            pass
            
            total_amount += nontax_total
            invoice.total_amount = total_amount
            if hasattr(invoice, 'vat_applicable'): invoice.vat_applicable = apply_vat
            if hasattr(invoice, 'vat_percentage'): invoice.vat_percentage = vat_percentage
            if hasattr(invoice, 'vat_amount'): invoice.vat_amount = vat_amount
            if hasattr(invoice, 'subtotal_amount'): invoice.subtotal_amount = subtotal_amount
            if hasattr(invoice, 'nontax_total'): invoice.nontax_total = nontax_total
            
            invoice.status = 'FINAL'
            invoice.save()
            
            # Update invoice products
            InvoiceProduct.objects.filter(invoice=invoice).delete()
            for p in products_data:
                InvoiceProduct.objects.create(invoice=invoice, product_description=p['desc'], quantity=p['qty'], unit_price=p['price'], total=p['total'], is_taxable=True)
            for n in nontax_data:
                InvoiceProduct.objects.create(invoice=invoice, product_description=n['desc'], quantity=n['qty'], unit_price=n['price'], total=n['total'], is_taxable=False)
            
            # Clear authorization after successful edit
            if auth_key in request.session:
                del request.session[auth_key]
            
            messages.success(request, f'Invoice {invoice.invoice_number} has been updated successfully!')
            return redirect('home:invoice_detail', invoice_id=invoice.id)
    else:
        form = CashInvoiceForm(instance=invoice)
    
    taxable_products = invoice.products.filter(is_taxable=True)
    nontax_items = invoice.products.filter(is_taxable=False)
    
    return render(request, 'home/cash_invoice.html', {
        'form': form,
        'edit_mode': True,
        'invoice': invoice,
        'taxable_products': taxable_products,
        'nontax_items': nontax_items,
        'require_password': invoice.status == 'FINAL' and not is_authorized,
        'password_verified': is_authorized,
    })


def invoice_detail(request, invoice_id):
    try:
        invoice = get_object_or_404(CashInvoice, id=invoice_id)
        all_products = InvoiceProduct.objects.filter(invoice=invoice)
        
        products_data = [] # Taxable products
        nontax_data = []   # Non-tax products
        
        subtotal_amount = Decimal('0.00')
        nontax_total = Decimal('0.00')
        
        for product in all_products:
            # Check if product is taxable (default to True if field doesn't exist yet)
            is_taxable = getattr(product, 'is_taxable', True)
            
            item_data = {
                'desc': product.product_description,
                'qty': product.quantity,
                'price': product.unit_price,
                'total': product.total
            }
            
            if is_taxable:
                products_data.append(item_data)
                subtotal_amount += product.total
            else:
                nontax_data.append(item_data)
                nontax_total += product.total
        
        # Handle VAT calculations
        vat_applicable = getattr(invoice, 'vat_applicable', False)
        vat_percentage = getattr(invoice, 'vat_percentage', Decimal('0.00'))
        vat_amount = getattr(invoice, 'vat_amount', Decimal('0.00'))
        stored_subtotal = getattr(invoice, 'subtotal_amount', Decimal('0.00'))
        stored_nontax_total = getattr(invoice, 'nontax_total', Decimal('0.00'))
        
        # Convert to Decimal for consistent calculations
        vat_percentage = Decimal(str(vat_percentage)) if vat_percentage else Decimal('0.00')
        vat_amount = Decimal(str(vat_amount)) if vat_amount else Decimal('0.00')
        stored_subtotal = Decimal(str(stored_subtotal)) if stored_subtotal else Decimal('0.00')
        stored_nontax_total = Decimal(str(stored_nontax_total)) if stored_nontax_total else Decimal('0.00')
        total_amount = Decimal(str(invoice.total_amount)) if invoice.total_amount else Decimal('0.00')
        
        # Use stored values if available (preferred), otherwise use calculated
        final_subtotal = stored_subtotal if stored_subtotal > 0 else subtotal_amount
        final_nontax_total = stored_nontax_total if stored_nontax_total > 0 else nontax_total
        
        # Recalculate VAT and total based on stored data if needed
        if vat_applicable and vat_percentage > 0:
            if vat_amount == 0:
                vat_amount = (final_subtotal * vat_percentage) / Decimal('100')
        else:
            vat_amount = Decimal('0.00')
            vat_percentage = Decimal('0.00')
            vat_applicable = False
            
        # Ensure total matches components
        # calculated_total = final_subtotal + vat_amount + final_nontax_total
        
        # Prepare invoice data for template
        invoice_data = {
            'invoice_number': invoice.invoice_number,
            'customer_name': invoice.customer_name,
            'date': invoice.date,
            'customer_address': invoice.customer_address,
            'subtotal_amount': round(final_subtotal, 2),
            'vat_applicable': vat_applicable,
            'vat_percentage': round(vat_percentage, 2),
            'vat_amount': round(vat_amount, 2),
            'nontax_items': nontax_data,
            'nontax_total': round(final_nontax_total, 2),
            'total_amount': round(total_amount, 2),
            'customer_sign': invoice.customer_sign,
            'manager_sign': invoice.manager_sign,
            'products': products_data
        }
        
        return render(request, 'home/invoice_detail.html', {
            'invoice_data': invoice_data,
            'invoice': invoice,
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





