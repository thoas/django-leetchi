import logging

from django import forms
from django.utils.translation import ugettext_lazy as _

from djleetchi.api import handler
from djleetchi.helpers import get_payer

from leetchi.exceptions import APIError, DecodeError
from leetchi import resources

logger_leetchi = logging.getLogger('leetchi')


class NewWithdrawalForm(models.ModelForm):

    class Meta:
        model = Withdrawal
        fields = ('bank_account_bic', 'bank_account_iban',
                  'bank_account_owner_address', 'bank_account_owner_name',
                  'amount', 'client_fee_amount', )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)

        super(NewWithdrawalForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        try:
            self.instance.content_object = self.user

            sync = kwargs.pop('sync', True)

            withdrawal = super(NewWithdrawalForm, self).save(*args, **kwargs)

            if sync is True:
                withdrawal.sync()

        except (APIError, DecodeError) as e:
            logger_leetchi.error(e)
            return False
        else:
            return withdrawal


class NewContributionForm(forms.ModelForm):
    amount = forms.CharField(label=_('Amount'),
                             widget=forms.TextInput,
                             help_text=_('Value in decimal, e.g. 20.50e'))

    class Meta:
        model = Contribution
        fields = ('amount', )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.content_object = kwargs.pop('content_object', None)

        super(NewContributionForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        try:
            self.instance.content_object = self.content_object
            self.instance.user = request.user
            self.instance.wallet_id = 0
            self.instance.amount = int(float(self.cleaned_data.get('amount')) * 100)
            self.instance.return_url = kwargs.pop('return_url', None)
            self.instance.template_url = kwargs.pop('template_url', None)

            sync = kwargs.pop('sync', True)

            contribution = super(NewContributionForm, self).save(self, *args, **kwargs)

            if sync is True:
                contribution.sync()
        except (APIError, DecodeError) as e:
            logger_leetchi.error(e)
            return False
        else:
            return contribution


class NewTransferForm(forms.ModelForm):
    amount = forms.CharField(label=_('Amount'),
                             widget=forms.TextInput,
                             help_text=_('Value in decimal, e.g. 20.50e'))

    class Meta:
        model = Transfer
        fields = ('amount', )

    def __init__(self, *args, **kwargs):
        self.payer = kwargs.pop('user', None)
        self.beneficiary = kwargs.pop('beneficiary', None)

        super(NewTransferForm, self).__init__(*args, **kwargs)

    def clean_amount(self):
        payer = get_payer(self.payer)

        amount = self.cleaned_data.get('amount')

        if not self.is_personal_amount_enough(payer, amount):
            raise forms.ValidationError(_('Your personal amount %(personal_amount)s is not enough to make this transfer %(amount)s' % {
                'personal_amount': payer.personal_wallet_amount_converted,
                'amount': amount
            }))

        return amount

    def is_personal_amount_enough(self, payer, amount):
        personal_amount = payer.personal_wallet_amount_converted

        return personal_amount >= float(amount)

    def save(self, *args, **kwargs):
        try:
            self.instance.content_object = self.beneficiary
            self.instance.user = self.payer
            self.instance.payer = self.payer
            self.instance.amount = int(float(self.cleaned_data.get('amount')) * 100)
            self.instance.beneficiary = self.beneficiary
            self.instance.beneficiary_wallet_id = 0

            sync = kwargs.pop('sync', True)

            transfer = super(NewTransferForm, self).save(*args, **kwargs)

            if sync is True:
                transfer.sync()

        except (APIError, DecodeError) as e:
            logger_leetchi.error(e)
            return False
        else:
            return transfer
