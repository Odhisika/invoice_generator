// static/js/script.js

document.addEventListener('DOMContentLoaded', function() {
    // For the Cash Invoice form
    const addProductButton = document.getElementById('add-product');
    if (addProductButton) {
        addProductButton.addEventListener('click', addProductRow);
        
        // Initialize the first row calculations
        const firstRow = document.querySelector('.product-row');
        if (firstRow) {
            setupProductRowEvents(firstRow);
        }
        
        // Enable remove button if there's more than one row
        updateRemoveButtons();
    }
});

function addProductRow() {
    const productRows = document.getElementById('product-rows');
    const rowCount = productRows.children.length + 1;
    
    const newRow = document.createElement('div');
    newRow.className = 'product-row';
    newRow.dataset.row = rowCount;
    
    newRow.innerHTML = `
        <div class="col-num">${rowCount}</div>
        <div class="col-desc">
            <input type="text" name="product_desc_${rowCount}" required>
        </div>
        <div class="col-qty">
            <input type="number" name="product_qty_${rowCount}" value="1" min="1" required>
        </div>
        <div class="col-price">
            <input type="number" name="product_price_${rowCount}" step="0.01" required>
        </div>
        <div class="col-total">
            <input type="number" name="product_total_${rowCount}" step="0.01" readonly>
        </div>
        <div class="col-action">
            <button type="button" class="btn remove-btn">×</button>
        </div>
    `;
    
    productRows.appendChild(newRow);
    setupProductRowEvents(newRow);
    updateRemoveButtons();
}

function setupProductRowEvents(row) {
    const qtyInput = row.querySelector('input[name^="product_qty"]');
    const priceInput = row.querySelector('input[name^="product_price"]');
    const totalInput = row.querySelector('input[name^="product_total"]');
    const removeButton = row.querySelector('.remove-btn');
    
    // Calculate total when quantity or price changes
    qtyInput.addEventListener('input', () => calculateRowTotal(row));
    priceInput.addEventListener('input', () => calculateRowTotal(row));
    
    // Remove row when remove button is clicked
    if (removeButton) {
        removeButton.addEventListener('click', () => {
            row.remove();
            renumberRows();
            updateTotalAmount();
            updateRemoveButtons();
        });
    }
}

function calculateRowTotal(row) {
    const qtyInput = row.querySelector('input[name^="product_qty"]');
    const priceInput = row.querySelector('input[name^="product_price"]');
    const totalInput = row.querySelector('input[name^="product_total"]');
    
    const qty = parseFloat(qtyInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    const total = (qty * price).toFixed(2);
    
    totalInput.value = total;
    updateTotalAmount();
}

function updateTotalAmount() {
    const totalInputs = document.querySelectorAll('input[name^="product_total"]');
    let grandTotal = 0;
    
    totalInputs.forEach(input => {
        grandTotal += parseFloat(input.value) || 0;
    });
    
    const totalAmountInput = document.getElementById('total_amount');
    if (totalAmountInput) {
        totalAmountInput.value = grandTotal.toFixed(2);
    }
}

function renumberRows() {
    const rows = document.querySelectorAll('.product-row');
    rows.forEach((row, index) => {
        const rowNum = index + 1;
        row.dataset.row = rowNum;
        row.querySelector('.col-num').textContent = rowNum;
        
        // Update input names
        const inputs = row.querySelectorAll('input');
        inputs.forEach(input => {
            const name = input.name;
            const newName = name.replace(/\d+/, rowNum);
            input.name = newName;
        });
    });
}

function updateRemoveButtons() {
    const rows = document.querySelectorAll('.product-row');
    const removeButtons = document.querySelectorAll('.remove-btn');
    
    removeButtons.forEach(button => {
        button.disabled = rows.length <= 1;
    });
}