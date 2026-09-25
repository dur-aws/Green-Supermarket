import json

from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from accounts.mixins import RBACPermissionMixin
from sales.models import Sale

from .models import Payment
from .services import PaymentProcess
from .services import FonepayService


class PaymentHistoryView(RBACPermissionMixin, ListView):
    model = Payment
    template_name = "payments/payment_history.html"
    context_object_name = "payments"
    paginate_by = 25
    module_name = "sales"
    required_permission = "view"

    def get_queryset(self):
        queryset = Payment.objects.select_related(
            "sale", "purchase", "purchase__supplier", "created_by"
        ).order_by("-created_at", "-transaction_id")

        payment_type = self.request.GET.get("type", "").strip().lower()
        if payment_type == "sales":
            queryset = queryset.filter(sale__isnull=False)
        elif payment_type == "purchases":
            queryset = queryset.filter(purchase__isnull=False)

        method = self.request.GET.get("method", "").strip().upper()
        if method in {"CASH", "FONEPAY"}:
            queryset = queryset.filter(payment_method=method)

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(internal_reference__icontains=query)
                | Q(provider_transaction_id__icontains=query)
                | Q(sale__invoice_no__icontains=query)
                | Q(sale__buyer_name__icontains=query)
                | Q(purchase__invoice_number__icontains=query)
                | Q(purchase__supplier__supplier_name__icontains=query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_payments = self.get_queryset()
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context.update(
            {
                "query": self.request.GET.get("q", "").strip(),
                "payment_type": self.request.GET.get("type", "").strip().lower(),
                "payment_method": self.request.GET.get("method", "").strip().upper(),
                "total_amount": filtered_payments.filter(status="PAID").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0,
                "paid_count": filtered_payments.filter(status="PAID").count(),
                "pagination_query": query_params.urlencode(),
            }
        )
        return context


@require_POST
def create_fonepay_payment(request):

    try:

        data = json.loads(request.body)

        sale_id = data.get("sale_id")

        if not sale_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Sale ID is required."
                },
                status=400
            )

        sale = Sale.objects.get(
            sales_id=sale_id
        )

        payment = sale.payment_transactions.filter(
            payment_method="FONEPAY",
            status__in=["PENDING", "PROCESSING"],
        ).order_by("transaction_id").first()
        if payment is None:
            result = PaymentProcess.create_payment(sale=sale, payment_method="FONEPAY")
            payment = sale.payment_transactions.get(transaction_id=result["payment_id"])

        payment = FonepayService.generate_qr(payment)

        return JsonResponse({
            "success": True,
            "payment_id": payment.transaction_id,
            "invoice_no": sale.invoice_no,
            "amount": str(payment.amount),
            "reference": payment.internal_reference,
            "qr_data": payment.qr_payload,
            "status": payment.status,
        })

    except Sale.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "Sale not found."
            },
            status=404
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e)
            },
            status=400
        )

from django.http import JsonResponse
from .models import Payment


def payment_status(request, payment_id):

    try:

        payment = Payment.objects.get(
            transaction_id=payment_id
        )

        return JsonResponse({
            "success": True,
            "payment_id": payment.transaction_id,
            "status": payment.status,
            "amount": str(payment.amount),
            "reference": payment.internal_reference,
        })

    except Payment.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "Payment transaction not found."
            },
            status=404
        )

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View


from .services import PaymentVerificationService   # adjust import path
from .models import Payment


@method_decorator(csrf_exempt, name="dispatch")
class PaymentVerificationView(View):
    """
    Endpoint to verify and mark a payment as SUCCESS.
    """

    def post(self, request, *args, **kwargs):
        try:
            payment_id = request.POST.get("payment_id")
            provider_txn_id = request.POST.get("provider_transaction_id")
            provider_ref = request.POST.get("provider_reference")

            if not payment_id:
                return JsonResponse(
                    {"status": "error", "message": "Missing payment_id"},
                    status=400,
                )

            # Call the service
            payment = PaymentVerificationService.mark_success(
                payment_id=payment_id,
                provider_transaction_id=provider_txn_id,
                provider_reference=provider_ref,
            )

            return JsonResponse({
                "status": "success",
                "payment_id": payment.transaction_id,
                "sale_id": payment.sale.sales_id,
                "amount": float(payment.amount),
                "payment_status": payment.status,
                "sale_status": payment.sale.sale_status,
            })

        except Payment.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Payment not found"},
                status=404,
            )
        except ValueError as e:
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=400,
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": "Unexpected error: " + str(e)},
                status=500,
            )
