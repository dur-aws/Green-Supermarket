from django.urls import path

from .views import (
    PaymentHistoryView,
    PaymentVerificationView,
    create_fonepay_payment,
    payment_status,
)


urlpatterns = [
    path("history/", PaymentHistoryView.as_view(), name="payment_history"),

    path("fonepay/create/", create_fonepay_payment, name="create_fonepay_payment"),

    path("<int:payment_id>/status/",payment_status,name="payment_status"),

    path("fonepay/verify/", PaymentVerificationView.as_view(),name="verify_fonepay_payment"),
]