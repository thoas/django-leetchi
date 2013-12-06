from datetime import datetime

from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from .fields import ResourceField
from .helpers import get_payer
from .compat import User
from .tasks import sync_resource

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

    def sync(self, async=False, commit=True):
        if async is False:

            parameters = self.request_parameters()

            field_name = self.Api.resource_field

            resource = self._meta.get_field(field_name).to(**parameters)

            setattr(self, field_name, resource)

            if commit:
                self.save()
        else:
            self.save()

            sync_resource.delay(self.__class__, self.pk)


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
        db_table = 'leetchi_contribution'

    class Api:
        resource_field = 'contribution'

    @property
    def real_amount(self):
        return self.amount / 100

    def request_parameters(self):
        user = get_payer(self.user)

        data = {
            'user_id': user.get_pk(),
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
        db_table = 'leetchi_transfer'

    class Api:
        resource_field = 'transfer'

    def request_parameters(self):
        payer = get_payer(self.payer)

        beneficiary = get_payer(self.beneficiary)

        return {
            'payer_id': payer.get_pk(),
            'beneficiary_id': beneficiary.get_pk(),
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

    class Api:
        resource_field = 'transfer_refund'

    def request_parameters(self):
        user = get_payer(self.user)

        return {
            'user_id': user.get_pk(),
            'transfer_id': self.transfer.transfer_id,
            'tag': self.get_tag()
        }


class Refund(BaseLeetchi):
    user = models.ForeignKey(User)
    refund = ResourceField(resources.Refund)
    contribution = models.ForeignKey(Contribution)
    is_success = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    class Api:
        resource_field = 'refund'

    class Meta:
        db_table = 'leetchi_refund'

    def request_parameters(self):
        return {
            'user_id': get_payer(self.user).get_pk(),
            'contribution_id': self.contribution.contribution_id,
            'tag': self.get_tag()
        }


class Withdrawal(BaseLeetchi):
    amount = models.IntegerField(help_text=_(u'Amount to transfer (in cents, ex: 51900)'),
                                 null=True)
    client_fee_amount = models.IntegerField(help_text=_(u'Amount to transfer with tax (ex: 4152 = 51900 * 8%)'),
                                            null=True)
    bank_account_owner_name = models.CharField(max_length=255,
                                               help_text=_(u'Name of bank account owner'),
                                               null=True)
    bank_account_owner_address = models.CharField(max_length=255,
                                                  help_text=_(u'Address of bank account owner'),
                                                  null=True)
    bank_account_iban = models.CharField(max_length=255,
                                         help_text=_(u'IBAN of bank account owner'),
                                         null=True)
    bank_account_bic = models.CharField(max_length=255,
                                        help_text=_(u'BIC of bank account owner'),
                                        null=True)

    withdrawal = ResourceField(resources.Withdrawal)


class WalletManager(models.Manager):
    def get_for_model(self, instance):
        try:
            content_type = ContentType.objects.get_for_model(instance)
            return (self.filter(content_type=content_type,
                                object_id=instance.pk)
                    .order_by('creation_date')[0])
        except IndexError:
            return None


class Wallet(BaseLeetchi):
    user = ResourceField(resources.User, null=True, blank=True)
    wallet = ResourceField(resources.Wallet, null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    objects = WalletManager()

    class Meta:
        unique_together = (
            ('wallet', 'content_type', 'object_id'),
        )
        db_table = 'leetchi_wallet'


class Beneficiary(models.Model):
    user = models.ForeignKey(User)
    beneficiary = ResourceField(resources.Beneficiary)
    bank_account_owner_name = models.CharField(max_length=255)
    bank_account_owner_address = models.CharField(max_length=255)
    bank_account_iban = models.CharField(max_length=100)
    bank_account_bic = models.CharField(max_length=100)
    creation_date = models.DateTimeField(default=datetime.now)

    class Meta:
        db_table = 'leetchi_beneficiary'

    class Api:
        resource_field = 'beneficiary'

    def request_parameters(self):
        return {
            'user': get_payer(self.user),
            'bank_account_bic': self.bank_account_bic,
            'bank_account_iban': self.bank_account_iban,
            'bank_account_owner_address': self.bank_account_owner_address,
            'bank_account_owner_name': self.bank_account_owner_name
        }


class StrongAuthentication(models.Model):
    strong_authentication = ResourceField(resources.StrongAuthentication)

    user = models.ForeignKey(User)
    beneficiary = models.ForeignKey(Beneficiary,
                                    related_name='strong_authentication',
                                    null=True, blank=True)

    is_completed = models.BooleanField(default=False)
    is_succeeded = models.BooleanField(default=False)
    creation_date = models.DateTimeField(default=datetime.now)

    class Meta:
        db_table = 'leetchi_strongauthentication'

    class Api:
        resource_field = 'strong_authentication'

    def request_parameters(self):
        beneficiary = None

        if self.beneficiary:
            beneficiary = self.beneficiary.beneficiary_id

        return {
            'user': get_payer(self.user),
            'beneficiary_id': beneficiary
        }
