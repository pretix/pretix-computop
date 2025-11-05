import hashlib
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pretix.base.models import Order, OrderPayment
from pretix.base.payment import PaymentException
from pretix.helpers import OF_SELF
from pretix.multidomain.urlreverse import eventreverse


class ComputopOrderView:
    def dispatch(self, request, *args, **kwargs):
        try:
            self.order = request.event.orders.get(code=kwargs["order"])
            if (
                hashlib.sha1(self.order.secret.lower().encode()).hexdigest()
                != kwargs["hash"].lower()
            ):
                raise Http404("Unknown order")
        except Order.DoesNotExist:
            # Do a hash comparison as well to harden timing attacks
            if (
                "abcdefghijklmnopq".lower()
                == hashlib.sha1("abcdefghijklmnopq".encode()).hexdigest()
            ):
                raise Http404("Unknown order")
            else:
                raise Http404("Unknown order")
        return super().dispatch(request, *args, **kwargs)

    def get_payment_for_update(self) -> OrderPayment:
        try:
            return self.order.payments.select_for_update(of=OF_SELF).get(
                pk=self.kwargs["payment"],
                provider__istartswith=self.kwargs["payment_provider"],
            )
        except OrderPayment.DoesNotExist:
            raise Http404("Unknown payment")

    def _redirect_to_order(self):
        return redirect(
            eventreverse(
                self.request.event,
                "presale:event.order",
                kwargs={"order": self.order.code, "secret": self.order.secret},
            )
            + ("?paid=yes" if self.order.status == Order.STATUS_PAID else "")
        )


@method_decorator(csrf_exempt, name="dispatch")
class ReturnView(ComputopOrderView, View):
    template_name = "pretix_computop/return.html"
    viewsource = "return_view"

    def read_and_process(self, request_body):
        if request_body.get("Data"):
            payment = self.get_payment_for_update()
            pprov = payment.payment_provider

            try:
                response = pprov.parse_data(request_body.get("Data"))
                if pprov.check_hash(response):
                    pprov.process_result(payment, response, self.viewsource)
                else:
                    messages.error(
                        self.request,
                        _(
                            "Sorry, we could not verify the authenticity of your request."
                            "Please contact the event organizer to get your payment verified manually."
                        ),
                    )
            except PaymentException as e:
                messages.error(self.request, str(e))
                return self._redirect_to_order()

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.read_and_process(request.POST)
        return self._redirect_to_order()

    @transaction.atomic
    def get(self, request, *args, **kwargs):
        self.read_and_process(request.GET)
        return self._redirect_to_order()


@method_decorator(csrf_exempt, name="dispatch")
class NotifyView(ComputopOrderView, View):
    template_name = "pretix_computop/return.html"
    viewsource = "notify_view"

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if request.POST.get("Data"):
            payment = self.get_payment_for_update()
            pprov = payment.payment_provider

            try:
                response = pprov.parse_data(request.POST.get("Data"))
            except PaymentException:
                return HttpResponseServerError()
            if pprov.check_hash(response):
                try:
                    payment = self.get_payment_for_update()
                    pprov.process_result(payment, response, self.viewsource)
                except PaymentException:
                    return HttpResponseServerError()
        return HttpResponse("[accepted]", status=200)
