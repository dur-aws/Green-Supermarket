class SaleError(Exception):
    """Base exception for all sale-related failures."""
    pass


class InsufficientStockError(SaleError):
    pass


class InvalidQuantityError(SaleError):
    pass


class InvalidDiscountError(SaleError):
    pass


class PaymentMismatchError(SaleError):
    pass