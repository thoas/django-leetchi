from collections import defaultdict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from djleetchi.util import load_class


def queryset_to_dict(qs, key='pk', singular=True):
    """
    Given a queryset will transform it into a dictionary based on ``key``.
    """
    if singular:
        result = {}
        for u in qs:
            result.setdefault(getattr(u, key), u)
    else:
        result = defaultdict(list)
        for u in qs:
            result[getattr(u, key)].append(u)
    return result

get_payer = getattr(settings, 'LEETCHI_PAYER_HELPER', None)

if not get_payer:
    raise ImproperlyConfigured('The required setting **LEETCHI_PAYER_HELPER** is missing.')
else:
    get_payer = load_class(get_payer)

get_wallet = getattr(settings, 'LEETCHI_WALLET_HELPER', None)

if not get_wallet:
    raise ImproperlyConfigured('The required setting **LEETCHI_WALLET_HELPER** is missing.')
else:
    get_wallet = load_class(get_wallet)
