# choices.py
PAYMENT_METHOD_CHOICES = (
    ('CASH', 'Cash'),
    ('CARD', 'Card / POS'),
    ('FONEPAY', 'Fonepay QR'),
    ('CREDIT', 'On Credit'),
    ('SPLIT', 'Split Payment'),
)

PAYMENT_STATUS_CHOICES = (
    ('PENDING', 'Pending Payment'),
    ('PROCESSING', 'Processing Payment'),
    ('PARTIAL', 'Partially Paid'),
    ('PAID', 'Paid / Settled'),
    ('FAILED', 'Payment Failed'),
    ('EXPIRED', 'Expired'),
    ('CANCELLED', 'Cancelled'),
    ('REFUNDED', 'Refunded'),
)

SALE_STATUS_CHOICES = (
    ('DRAFT', 'Draft'),
    ('PENDING', 'Pending Confirmation'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
    ('PARTIALLY_CREDITED', 'Partially Credited'),
    ('FULLY_CREDITED', 'Fully Credited'),
)