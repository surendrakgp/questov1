from authorize.client import AuthorizeClient, AuthorizeCreditCard
from authorize.data import Address, CreditCard


def get_client(authorize_id, authorize_key):
    return AuthorizeClient(authorize_id, authorize_key)


def get_card(card_num, cvn, exp_month, exp_year, fname, lname,
             street, city, state, zipcode, authorize_id, authorize_key,
             country='USA'):
    client = get_client(authorize_id, authorize_key)
    address = Address(street, city, state, zipcode, country)
    card = CreditCard(card_num, exp_year, exp_month, cvn, fname, lname)
    return AuthorizeCreditCard(client, card, address=address)


def charge_card(amount, card):
    return card.capture(amount)


def settle_transaction(transaction):
    return transaction.settle()


def authorize_card(amount, card):
    return card.auth(amount)