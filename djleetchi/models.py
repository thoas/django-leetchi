from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from djleetchi.fields import ResourceField

from djleetchi import handler

from leetchi.resources import (Contribution as LeetchiContribution,
                               Transfer as LeetchiTransfer,
                               Refund as LeetchiRefund,
                               Withdrawal as LeetchiWithdrawal,
                               TransferRefund as LeetchiTransferRefund,
                               Wallet as LeetchiWallet)


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


class Contribution(BaseLeetchi):
    TYPE_PAYLINE = 1
    TYPE_OGONE = 2
    TYPE_CHOICES = (
        (TYPE_PAYLINE, 'Payline'),
        (TYPE_OGONE, 'Ogone'),
    )

    contribution = ResourceField(LeetchiContribution)
    wallet = ResourceField(LeetchiWallet)
    amount = models.IntegerField()
    user = models.ForeignKey(User)
    client_fee_amount = models.IntegerField(default=0)
    return_url = models.CharField(null=True, blank=True, max_length=255)
    template_url = models.CharField(null=True, blank=True, max_length=255)
    is_completed = models.BooleanField(default=False)
    is_success = models.BooleanField(default=False)
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES,
                                            default=TYPE_PAYLINE, verbose_name=_('Type'),
                                            db_index=True)

    @property
    def real_amount(self):
        return self.amount / 100

    def save(self, **kwargs):
        if not self.pk and not self.contribution_id:
            account_user = self.user

            if 'user' in kwargs:
                account_user = kwargs.pop('user')

            user, created = account_user.get_profile().get_payer()

            data = {
                'user': user,
                'amount': self.amount,
                'client_fee_amount': self.client_fee_amount,
                'return_url': self.return_url,
                'wallet_id': self.wallet_id,
                'tag': self.get_tag()
            }

            if hasattr(self, 'type') and self.type:
                data['type'] = self.get_type_display()

            if hasattr(self, 'culture') and self.culture:
                data['culture'] = self.culture

            if self.template_url:
                data['template_url'] = self.template_url

            contribution = LeetchiContribution(**data)

            contribution.save(handler)

            self.contribution = contribution

        super(Contribution, self).save(**kwargs)


class TransferManager(models.Manager):
    def create_from_transfer(self, transfer, payer, wallet, beneficiary, content_object=None, commit=True):
        if isinstance(transfer, int):
            transfer = LeetchiTransfer.get(transfer, handler)

        klass = self.model

        resource = klass()
        resource.transfer = transfer
        resource.amount = transfer.amount
        resource.payer = payer

        if not content_object:
            tag = transfer.tag

            app, pk = tag.split(':')
            model_class = models.model(*app.split('.'))

            content_object = model_class.objects.get(pk=pk)

        resource.content_object = content_object
        resource.beneficiary_wallet = wallet
        resource.beneficiary = beneficiary

        if commit:
            resource.save()

        return resource


class Transfer(BaseLeetchi):
    transfer = ResourceField(LeetchiTransfer)
    beneficiary_wallet = ResourceField(LeetchiWallet)
    payer = models.ForeignKey(User, related_name='payers')
    beneficiary = models.ForeignKey(User, related_name='beneficiaries')
    amount = models.IntegerField()

    objects = TransferManager()

    def save(self, **kwargs):
        if not self.pk and not self.transfer_id:
            payer, created = self.payer.get_profile().get_payer()

            beneficiary, created = self.beneficiary.get_profile().get_payer()

            transfer = LeetchiTransfer(**{
                'payer': payer,
                'beneficiary': beneficiary,
                'tag': self.get_tag(),
                'amount': self.amount,
                'beneficiary_wallet_id': self.beneficiary_wallet_id
            })

            transfer.save(handler)

            self.transfer = transfer

        super(Transfer, self).save(**kwargs)


class TransferRefund(BaseLeetchi):
    transfer_refund = ResourceField(LeetchiTransferRefund)
    transfer = models.ForeignKey(Transfer)
    user = models.ForeignKey(User)

    class Meta:
        verbose_name = 'transferrefund'

    def save(self, **kwargs):
        if not self.pk and not self.transfer_refund_id:
            user, created = self.user.get_profile().get_payer()

            transfer_refund = LeetchiTransferRefund(**{
                'user': user,
                'transfer': self.get_transfer(),
                'tag': self.get_tag()
            })

            transfer_refund.save(handler)

            self.transfer_refund = transfer_refund

        super(TransferRefund, self).save(**kwargs)

    def get_transfer(self):
        return self.transfer.transfer


class Refund(BaseLeetchi):
    user = models.ForeignKey(User)
    refund = ResourceField(LeetchiRefund)
    contribution = models.ForeignKey(Contribution)
    is_success = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    def save(self, **kwargs):
        if not self.pk and not self.refund_id:
            user, created = self.user.get_profile().get_payer()

            refund = LeetchiRefund(**{
                'user': user,
                'contribution': self.get_contribution(),
                'tag': self.get_tag(),
            })

            refund.save(handler)

            self.refund = refund

        super(Refund, self).save(**kwargs)

    def get_contribution(self):
        return self.contribution.contribution


class Withdrawal(BaseLeetchi):
    withdrawal = ResourceField(LeetchiWithdrawal)


class Wallet(BaseLeetchi):
    wallet = ResourceField(LeetchiWallet, null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)
