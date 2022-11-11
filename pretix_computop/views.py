import hashlib
from django.contrib import messages
from django.http import Http404, HttpResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pretix.base.models import Order
from pretix.base.payment import PaymentException
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

    @cached_property
    def pprov(self):
        return self.payment.payment_provider

    @property
    def payment(self):
        return get_object_or_404(
            self.order.payments,
            pk=self.kwargs["payment"],
            provider__istartswith=self.kwargs["payment_provider"],
        )

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
            try:
                response = self.pprov.parse_data(request_body.get("Data"))
                if self.pprov.check_hash(response):
                    self.pprov.process_result(self.payment, response, self.viewsource)
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

    def post(self, request, *args, **kwargs):
        self.read_and_process(request.POST)
        return self._redirect_to_order()

    def get(self, request, *args, **kwargs):
        self.read_and_process(request.GET)
        return self._redirect_to_order()


@method_decorator(csrf_exempt, name="dispatch")
class NotifyView(ComputopOrderView, View):
    template_name = "pretix_computop/return.html"
    viewsource = "notify_view"

    def post(self, request, *args, **kwargs):
        if request.POST.get("Data"):
            try:
                response = self.pprov.parse_data(request.POST.get("Data"))
            except PaymentException:
                HttpResponseServerError()
            if self.pprov.check_hash(response):
                try:
                    self.pprov.process_result(self.payment, response, self.viewsource)
                except PaymentException:
                    return HttpResponseServerError()
        return HttpResponse("[accepted]", status=200)
