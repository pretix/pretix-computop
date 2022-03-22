import hashlib

from cached_property import cached_property
from django.http import Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View

from pretix.base.models import Order
from pretix.multidomain.urlreverse import eventreverse


class FirstcashOrderView:
    def __init__(self):
        self.order = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.order = request.event.orders.get(code=kwargs['order'])
            if hashlib.sha1(self.order.secret.lower().encode()).hexdigest() != kwargs['hash'].lower():
                raise Http404('Unknown order')
            # todo: Vergleiche Order-Code und Self.payment.….code
            test = self.payment.payment_provider
        except Order.DoesNotExist:
            # Do a hash comparison as well to harden timing attacks
            if 'abcdefghijklmnopq'.lower() == hashlib.sha1('abcdefghijklmnopq'.encode()).hexdigest():
                raise Http404('Unknown order')
            else:
                raise Http404('Unknown order')
        return super().dispatch(request, *args, **kwargs)

    @cached_property
    def pprov(self):
        return self.payment.payment_provider

    @property
    def payment(self):
        return get_object_or_404(
            self.order.payments,
            pk=self.kwargs['payment'],
            provider='1cs',
        )

    def _redirect_to_order(self):
        return redirect(eventreverse(self.request.event, 'presale:event.order', kwargs={
            'order': self.order.code,
            'secret': self.order.secret
        }) + ('?paid=yes' if self.order.status == Order.STATUS_PAID else ''))


class ReturnView(FirstcashOrderView, View):
    template_name = 'pretix_firstcash/return.html'

    # Status überprüfen (Failed, Success,…) Gibt es Pending o.ä.?
    # payment success Funktionen

    # Parameter in payment.info schicken, status setzen

    def get(self, request, *args, **kwargs):
        # return self._redirect_to_order()
        return render(request, self.template_name)


class NotifyView(ReturnView, FirstcashOrderView, View):
    pass
