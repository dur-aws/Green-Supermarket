document.addEventListener('DOMContentLoaded', function () {

    const itemRows = document.getElementById('item-rows');
    const productSearch = document.getElementById('product-search');
    const productSuggestions = document.getElementById('product-suggestions');
    const customerSearch = document.getElementById('customer-search');
    const customerSuggestions = document.getElementById('customer-suggestions');
    const customerIdInput = document.getElementById('customer-id');
    const receivedInput = document.getElementById('received-amount');

    let cart = [];        // in-memory cart, source of truth for preview
    let rowCounter = 0;

    // ---------- PRODUCT SEARCH ----------
    let productDebounce;
    productSearch.addEventListener('input', function () {
        clearTimeout(productDebounce);
        const query = this.value.trim();
        if (query.length < 2) { productSuggestions.classList.remove('active'); return; }

        productDebounce = setTimeout(() => {
            fetch(`/sales/product-search/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => renderProductSuggestions(data.results))
                .catch(() => showToast('Product search failed', 'error'));
        }, 300);
    });

    function renderProductSuggestions(products) {
        productSuggestions.innerHTML = '';
        if (!products.length) { productSuggestions.classList.remove('active'); return; }

        products.forEach(p => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            const lowStock = p.stock <= p.reorder_level;
            item.innerHTML = `${p.name}
                <span class="stock-tag ${lowStock ? 'low' : ''}">${p.stock} ${p.unit}</span>`;
            item.addEventListener('click', () => {
                addItemToCart(p);
                productSearch.value = '';
                productSuggestions.classList.remove('active');
            });
            productSuggestions.appendChild(item);
        });
        productSuggestions.classList.add('active');
    }

    // ---------- CUSTOMER SEARCH ----------
    let customerDebounce;
    customerSearch.addEventListener('input', function () {
        clearTimeout(customerDebounce);
        const query = this.value.trim();
        if (query.length < 2) { customerSuggestions.classList.remove('active'); return; }

        customerDebounce = setTimeout(() => {
            fetch(`/sales/api/customer-search/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => renderCustomerSuggestions(data.results))
                .catch(() => showToast('Customer search failed', 'error'));
        }, 300);
    });

    function renderCustomerSuggestions(customers) {
        customerSuggestions.innerHTML = '';
        if (!customers.length) { customerSuggestions.classList.remove('active'); return; }

        customers.forEach(c => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.textContent = `${c.name} ${c.phone ? '- ' + c.phone : ''}`;
            item.addEventListener('click', () => {
                customerIdInput.value = c.id;
                customerSearch.value = c.name;
                customerSuggestions.classList.remove('active');
            });
            customerSuggestions.appendChild(item);
        });
        customerSuggestions.classList.add('active');
    }

    document.addEventListener('click', function (e) {
        if (!e.target.closest('.search-wrap')) {
            productSuggestions.classList.remove('active');
            customerSuggestions.classList.remove('active');
        }
    });

    // ---------- CART / ROW MANAGEMENT ----------
    function addItemToCart(product) {
        const existing = cart.find(i => i.product_id === product.id);
        if (existing) {
            existing.quantity += 1;
        } else {
            rowCounter++;
            cart.push({
                row_id: rowCounter,
                product_id: product.id,
                name: product.product_name,
                closing_qty: product.stock,
                unit: product.unit,
                quantity: 1,
                rate: parseFloat(product.price),
                discount: 0,
                tax_percent: parseFloat(product.tax_percent) || 0,
            });
        }
        renderCart();
    }

    function renderCart() {
        itemRows.innerHTML = '';
        cart.forEach((item, idx) => {
            const tr = document.createElement('tr');
            tr.dataset.rowId = item.row_id;
            tr.innerHTML = `
                <td>${idx + 1}</td>
                <td>${item.name}</td>
                <td>${item.closing_qty} ${item.unit}</td>
                <td><input type="number" class="qty-input" min="1" value="${item.quantity}"></td>
                <td>${item.unit}</td>
                <td>${item.rate.toFixed(2)}</td>
                <td><input type="number" class="discount-input" min="0" value="${item.discount}"></td>
                <td><input type="number" class="tax-input" min="0" value="${item.tax_percent}"></td>
                <td class="amount-cell">0.00</td>
                <td>
                    <button type="button" class="row-action-btn row-delete-btn" title="Remove">✕</button>
                </td>
            `;
            itemRows.appendChild(tr);

            tr.querySelector('.qty-input').addEventListener('input', e => {
                const val = parseFloat(e.target.value);
                if (val > item.closing_qty) {
                    showToast(`Only ${item.closing_qty} ${item.unit} of ${item.name} in stock`, 'error');
                }
                item.quantity = val || 0;
                recalculateRow(tr, item);
            });
            tr.querySelector('.discount-input').addEventListener('input', e => {
                item.discount = parseFloat(e.target.value) || 0;
                recalculateRow(tr, item);
            });
            tr.querySelector('.tax-input').addEventListener('input', e => {
                item.tax_percent = parseFloat(e.target.value) || 0;
                recalculateRow(tr, item);
            });
            tr.querySelector('.row-delete-btn').addEventListener('click', () => {
                cart = cart.filter(i => i.row_id !== item.row_id);
                renderCart();
            });

            recalculateRow(tr, item);
        });
        recalculateFooterTotals();
    }

    function recalculateRow(tr, item) {
        let amount = (item.quantity * item.rate) - item.discount;
        amount += amount * (item.tax_percent / 100);
        tr.querySelector('.amount-cell').textContent = amount.toFixed(2);
        recalculateFooterTotals();
    }

    function recalculateFooterTotals() {
        let subtotal = 0, discountTotal = 0, taxTotal = 0;
        cart.forEach(item => {
            const base = item.quantity * item.rate;
            const afterDiscount = base - item.discount;
            const tax = afterDiscount * (item.tax_percent / 100);
            subtotal += base;
            discountTotal += item.discount;
            taxTotal += tax;
        });

        const rawGrand = subtotal - discountTotal + taxTotal;
        const grandTotal = Math.round(rawGrand);
        const roundOff = grandTotal - rawGrand;

        document.getElementById('subtotal').textContent = subtotal.toFixed(2);
        document.getElementById('discount-total').textContent = discountTotal.toFixed(2);
        document.getElementById('tax-total').textContent = taxTotal.toFixed(2);
        document.getElementById('round-off').textContent = roundOff.toFixed(2);
        document.getElementById('grand-total').textContent = grandTotal.toFixed(2);

        updateChange();
    }

    receivedInput.addEventListener('input', updateChange);
    function updateChange() {
        const grand = parseFloat(document.getElementById('grand-total').textContent) || 0;
        const received = parseFloat(receivedInput.value) || 0;
        document.getElementById('change-amount').textContent = (received - grand).toFixed(2);
    }

    // ---------- SAVE / CHECKOUT ----------
    const idempotencyKey = crypto.randomUUID();  // generated once per invoice session

    document.getElementById('save-btn').addEventListener('click', function () {
        if (!cart.length) { showToast('Cart is empty', 'error'); return; }

        this.disabled = true;  // prevent double-click submission

        const payload = {
            customer_id: customerIdInput.value,
            narration: document.getElementById('narration').value,
            idempotency_key: idempotencyKey,
            items: cart.map(i => ({
                product_id: i.product_id,
                quantity: i.quantity,
                discount: i.discount,
                tax_percent: i.tax_percent,
            })),
            payments: [
                { method: 'CASH', amount: parseFloat(receivedInput.value) || 0 }
            ],
        };

        fetch('/sales/checkout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(payload),
        })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(({ status, body }) => {
            if (status === 201) {
                showToast('Sale completed: ' + body.invoice_no, 'success');
                window.location.href = `/sales/${body.sale_id}/invoice/`;
            } else {
                showToast(body.error || 'Checkout failed', 'error');
                document.getElementById('save-btn').disabled = false;
            }
        })
        .catch(() => {
            showToast('Network error — please check and retry', 'error');
            document.getElementById('save-btn').disabled = false;
        });
    });

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.getElementById('toast-container').appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    }

    // Keyboard shortcut: F9 to save (common POS convention)
    document.addEventListener('keydown', e => {
        if (e.key === 'F9') { e.preventDefault(); document.getElementById('save-btn').click(); }
    });
});