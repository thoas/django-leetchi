import sys

from datetime import timedelta

from optparse import make_option

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone as datetime


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--gap',
                    action='store',
                    type='int',
                    dest='gap',
                    default=30,
                    help='Gap bettween two sync'),
        make_option('--range',
                    action='store',
                    type='int',
                    dest='range',
                    default=1000,
                    help='Range between each querysets'),
        make_option('--limit',
                    action='store',
                    type='int',
                    dest='limit',
                    default=None,
                    help='Limit wallets to sync'),
    )

    can_import_settings = True

    def handle(self, *args, **options):
        from leetchi.exceptions import APIError, DecodeError

        from djleetchi.models import Wallet

        qs = Wallet.objects.filter(models.Q(last_synced__lte=datetime.now() - timedelta(minutes=options.get('gap'))) |
                                   models.Q(last_synced__isnull=True)).order_by('last_synced', 'id')

        limit = options.get('limit', qs.count())

        for offset in range(0, limit, options.get('range')):

            wallets = qs[offset:offset + options.get('range')]

            for wallet in wallets:
                try:
                    user = wallet.user

                    wallet.amount = user.personal_wallet_amount
                    wallet.last_synced = datetime.now()

                    wallet.save(update_fields=('amount', 'last_synced'))

                    print u'Sync wallet for user %s' % user

                except (APIError, DecodeError), e:
                    sys.stdout.write(e)
