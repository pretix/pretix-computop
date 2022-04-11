import hashlib
import json
import urllib.parse

from cached_property import cached_property
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from pretix.base.models import Order
from pretix.multidomain.urlreverse import eventreverse

from .payment import ComputopMethod


class ComputopOrderView:
    def dispatch(self, request, *args, **kwargs):
        try:
            self.order = request.event.orders.get(code=kwargs['order'])
            if hashlib.sha1(self.order.secret.lower().encode()).hexdigest() != kwargs['hash'].lower():
                raise Http404('Unknown order')
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
            provider__istartswith=self.kwargs['payment_provider'],
        )

    def _redirect_to_order(self):
        return redirect(eventreverse(self.request.event, 'presale:event.order', kwargs={
            'order': self.order.code,
            'secret': self.order.secret
        }) + ('?paid=yes' if self.order.status == Order.STATUS_PAID else ''))

    @cached_property
    def pprov(self):
        return self.payment.payment_provider

    def _handle_data(self, data):
        response = self._parse_data(data)
        if self.pprov.check_hash(response):
            self.payment.info = json.dumps({'request': self.payment.info, 'response': response})
            self.payment.save(update_fields=['info'])  # todo: fix (payment not the correct object?)
            self._set_status_code(response['Code'][0], response)

    def _parse_data(self, data):
        payload = self.pprov.decrypt(data)
        return urllib.parse.parse_qs(payload)

    def _set_status_code(self, code, response):
        if code == '00000000':
            self.payment.confirm()
        else:
            messages.error(self.request, _('Your payment failed. Please try again.'))
            self.payment.fail(info={'request': self.payment.info, 'response': response})


@method_decorator(csrf_exempt, name='dispatch')
class ReturnView(ComputopOrderView, View):
    template_name = 'pretix_computop/return.html'

    def post(self, request, *args, **kwargs):
        if request.POST['Data']:
            data = str(request.POST.get('Data'))
            self._handle_data(data)
        return self._redirect_to_order()

    def get(self, request, *args, **kwargs):
        return self._redirect_to_order()


@method_decorator(csrf_exempt, name='dispatch')
class NotifyView(ReturnView, ComputopOrderView, View):
    def post(self, request, *args, **kwargs):
        if request.POST['Data']:
            data = str(request.POST.get('Data'))
            self._handle_data(data)
        print('notify', request.POST)
        return HttpResponse('[accepted]', status=200)
