from authorize import AuthorizeInvalidError, AuthorizeResponseError
from datetime import date
import random

from django.conf import settings

from postajob.payment import get_card, charge_card
from myjobs.tests.setup import MyJobsBase


class PaymentTests(MyJobsBase):
    def setUp(self):
        super(PaymentTests, self).setUp()
        self.card_info = {
            'card_num': random.choice([
                6011000000000012,
                4007000000027,
                5424000000000015]),
            'city': 'Indianapolis',
            'country': 'USA',
            'cvn': str(random.randint(0, 999)).zfill(3),
            'exp_month': (date.today().month + 1) % 12 or 12,
            'exp_year': date.today().year + 5,
            'fname': 'John',
            'lname': 'Smith',
            'street': '123 Street Rd.',
            'state': 'Indiana',
            'zipcode': 46268,
            'authorize_id': settings.TESTING_CC_AUTH['api_id'],
            'authorize_key': settings.TESTING_CC_AUTH['transaction_key']
        }

    def test_get_card(self):
        get_card(**self.card_info)

    def test_charge_card(self):
        card = get_card(**self.card_info)
        charge_card(random.randint(1, 5000), card)

    def test_get_card_invalid_card(self):
        self.card_info['card_num'] = 1
        self.assertRaises(AuthorizeInvalidError, get_card,
                          **self.card_info)

    def test_get_card_invalid_exp_date(self):
        self.card_info['exp_year'] = 2013
        self.assertRaises(AuthorizeInvalidError, get_card,
                          **self.card_info)

    def test_get_card_invalid_cvn(self):
        self.card_info['cvn'] = 'a'
        self.assertRaises(AuthorizeInvalidError, get_card,
                          **self.card_info)

    # The following tests require specific triggers to be used in
    # order to get a specific error. The errors can be found at:
    # http://developer.authorize.net/tools/errorgenerationguide/
    def test_charge_card_declined(self):
        card = get_card(**self.card_info)
        self.assertRaises(AuthorizeResponseError, charge_card,
                          70.02, card)
        self.assertRaises(AuthorizeResponseError, charge_card,
                          70.03, card)
        self.assertRaises(AuthorizeResponseError, charge_card,
                          70.05, card)

    def test_charge_card_invalid_cvn(self):
        self.card_info['cvn'] = 901
        card = get_card(**self.card_info)
        self.assertRaises(AuthorizeResponseError, charge_card,
                          70.02, card)
