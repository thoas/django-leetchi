import logging

from django import forms
from django.utils.translation import ugettext_lazy as _

from djleetchi.models import Contribution, Transfer, Withdrawal
from djleetchi.forms import WithdrawalForm
from djleetchi.api import handler
from djleetchi.helpers import get_payer

from leetchi.exceptions import APIError, DecodeError
from leetchi import resources

logger_leetchi = logging.getLogger('leetchi')


class NewWithdrawalForm(WithdrawalForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(NewWithdrawalForm, self).__init__(*args, **kwargs)

    def save(self):
        try:
            w = resources.Withdrawal()
            for field_name in ('bank_account_bic', 'bank_account_iban',
                               'bank_account_owner_address', 'bank_account_owner_name',
                               'amount', 'client_fee_amount'):
                setattr(w, field_name, self.cleaned_data[field_name])

            payer = get_payer(self.user)

            w.user = payer
            w.save(handler)

            withdrawal = Withdrawal()
            withdrawal.withdrawal = w
            withdrawal.content_object = self.user
            withdrawal.save()

        except (APIError, DecodeError) as e:
            logger_leetchi.error(e)
            return False
        else:
            return withdrawal


class NewContributionForm(forms.Form):
    amount = forms.CharField(label=_('Amount'),
                             widget=forms.TextInput,
                             help_text=_('Value in decimal, e.g. 20.50e'))

    def get_return_url(self):
        raise NotImplementedError

    def save(self, request, user, return_url, template_url=None):
        try:
            contribution = Contribution()
            contribution.content_object = user
            contribution.user = request.user
            contribution.wallet_id = 0
            contribution.amount = int(float(self.cleaned_data.get('amount')) * 100)
            contribution.return_url = self.get_return_url()

            contribution.save(user=user)
        except (APIError, DecodeError) as e:
            logger_leetchi.error(e)
            return False
        else:
            return contribution


class NewTransferForm(forms.Form):
    amount = forms.CharField(label=_('Amount'),
                             widget=forms.TextInput,
                             help_text=_('Value in decimal, e.g. 20.50e'))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(NewTransferForm, self).__init__(*args, **kwargs)

    def clean_amount(self):
        leetchi_user = get_payer(self.user)

        amount = self.cleaned_data.get('amount')

        if not self.is_personal_amount_enough(amount):
            raise forms.ValidationError(_('Your personal amount %(personal_amount)s is not enough to make this transfer %(amount)s' % {
                'personal_amount': leetchi_user.personal_wallet_amount_converted,
                'amount': amount
            }))

        return amount

    def is_personal_amount_enough(self, amount):
        leetchi_user = get_payer(self.user)

        personal_amount = leetchi_user.personal_wallet_amount_converted

        return personal_amount >= float(amount)

    def save(self, payer_user, beneficiary_user):
        try:
            transfer = Transfer()
            transfer.content_object = beneficiary_user
            transfer.user = payer_user
            transfer.payer = payer_user
            transfer.amount = int(float(self.cleaned_data.get('amount')) * 100)
            transfer.beneficiary = beneficiary_user
            transfer.beneficiary_wallet_id = 0
            transfer.save()
        except (APIError, DecodeError) as e:
            logger_leetchi.error(e)
            return False
        else:
            return transfer
