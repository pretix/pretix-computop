import json
import pytest
from datetime import timedelta
from decimal import Decimal
from django.test import override_settings
from django.utils.timezone import now
from django_scopes import scopes_disabled
from pretix.base.models import Event, Order, OrderPayment, Organizer


@pytest.fixture
@scopes_disabled()
def env():
    o = Organizer.objects.create(name='Dummy', slug='dummy')
    event = Event.objects.create(
        organizer=o, name='Dummy', slug='dummy', plugins='pretix_computop',
        date_from=now(), live=True
    )
    o1 = Order.objects.create(
        code='FOOBAR', event=event, email='dummy@dummy.test',
        status=Order.STATUS_PAID,
        datetime=now(), expires=now() + timedelta(days=10),
        total=Decimal('13.37'),
        sales_channel=o.sales_channels.get(identifier="web"),
    )
    p = o1.payments.create(
        amount=o1.total,
        provider='computop',
        state=OrderPayment.PAYMENT_STATE_CONFIRMED,
        info=json.dumps({
        })
    )
    return event, o1, p


@pytest.mark.django_db
@override_settings(DEBUG=False)  # debug page messes this up
def test_webhook_all_good(env, client):
    order = env[1]
    r = client.post(
        '/dummy/dummy/computop/notify/{}/{}/{}/'.format(
            order.code,
            order.tagged_secret("plugins:pretix_computop:notify"),
            env[2].pk,
        ),
        b"a=b&c=d",
        # computop sends the following content type with a charset
        # According to RFC 1866, the "application/x-www-form-urlencoded"
        # content type does not have a charset and should be always treated
        # as UTF-8.
        # Therefore, Django would crash out by default...
        content_type='application/x-www-form-urlencoded; charset=iso-8859-1'
    )
    assert r.status_code == 200

    order.refresh_from_db()
    assert order.status == Order.STATUS_PAID
