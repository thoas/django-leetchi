from datetime import datetime

from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from djleetchi.fields import ResourceField
from djleetchi.api import handler
from djleetchi.helpers import get_payer
from djleetchi.compat import User

from leetchi import resources


class BaseLeetchi(models.Model):
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType)
    creation_date = models.DateTimeField(default=datetime.now)

    class Meta:
        abstract = True

    def get_tag(self):
        return u'%s.%s:%d' % (self.content_type.app_label,
                              self.content_type.model,
                              self.object_id)

    def sync(self, async=False, commit=False):
        parameters = self.request_parameters()

        field_name = self._meta.resource_field
        resource = self._meta.get_field(field_name).to(**parameters)
        setattr(self, field_name, resource)

        if commit:
            self.save()


class Contribution(BaseLeetchi):
    TYPE_PAYLINE = 1
    TYPE_OGONE = 2
    TYPE_CHOICES = (
        (TYPE_PAYLINE, 'Payline'),
        (TYPE_OGONE, 'Ogone'),
    )

    contribution = ResourceField(resources.Contribution)
    wallet = ResourceField(resources.Wallet)
    amount = models.IntegerField()
    user = models.ForeignKey(User)
    client_fee_amount = models.IntegerField(default=0)
    return_url = models.CharField(null=True, blank=True, max_length=255)
    template_url = models.CharField(null=True, blank=True, max_length=255)
    is_completed = models.BooleanField(default=False)
    is_success = models.BooleanField(default=False)
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES,
                                            default=TYPE_PAYLINE,
                                            verbose_name=_('Type'),
                                            db_index=True)

    class Meta:
        resource_field = 'contribution'

    @property
    def real_amount(self):
        return self.amount / 100

    def request_parameters(self):
        user = get_payer(self.user)

        data = {
            'user': user,
            'amount': self.amount,
            'client_fee_amount': self.client_fee_amount,
            'return_url': self.return_url,
            'wallet_id': self.wallet_id,
            'tag': self.get_tag(),
            'template_url': self.template_url
        }

        if self.type:
            data['type'] = self.get_type_display()

        return data

    def sync_status(self, commit=True):
        contribution = self.contribution

        if contribution.is_success():
            self.is_success = True
            self.is_completed = True

        elif contribution.is_completed and not contribution.is_succeeded:
            self.is_success = False
            self.is_completed = True

        if commit:
            self.save()

    def is_error(self):
        return not self.is_success and self.is_completed


class Transfer(BaseLeetchi):
    transfer = ResourceField(resources.Transfer)
    beneficiary_wallet = ResourceField(resources.Wallet)
    payer = models.ForeignKey(User, related_name='payers')
    beneficiary = models.ForeignKey(User, related_name='beneficiaries')
    amount = models.IntegerField()

    class Meta:
        resource_field = 'transfer'

    def request_parameters(self):
        payer = get_payer(self.payer)

        beneficiary = get_payer(self.beneficiary)

        return {
            'payer': payer,
            'beneficiary': beneficiary,
            'tag': self.get_tag(),
            'amount': self.amount,
            'beneficiary_wallet_id': self.beneficiary_wallet_id
        }


class TransferRefund(BaseLeetchi):
    transfer_refund = ResourceField(resources.TransferRefund)
    transfer = models.ForeignKey(Transfer)
    user = models.ForeignKey(User)

    class Meta:
        verbose_name = 'transferrefund'
        resource_field = 'transfer_refund'

    def request_parameters(self):
        user = get_payer(self.user)

        return {
            'user': user,
            'transfer': self.transfer.transfer,
            'tag': self.get_tag()
        }


class Refund(BaseLeetchi):
    user = models.ForeignKey(User)
    refund = ResourceField(resources.Refund)
    contribution = models.ForeignKey(Contribution)
    is_success = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    class Meta:
        resource_field = 'refund'

    def request_parameters(self):
        return {
            'user': get_payer(self.user),
            'contribution': self.contribution.contribution,
            'tag': self.get_tag()
        }


class Withdrawal(BaseLeetchi):
    withdrawal = ResourceField(resources.Withdrawal)


class Wallet(BaseLeetchi):
    wallet = ResourceField(resources.Wallet, null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)
