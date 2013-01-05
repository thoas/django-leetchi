import logging

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib.sites.models import Site

from djleetchi.models import Contribution, Transfer, Withdrawal
from djleetchi.forms import WithdrawalForm

from leetchi.resources import Withdrawal as LeetchiWithdrawal
from leetchi.exceptions import APIError, DecodeError

from djleetchi import handler

import waffle

logger_leetchi = logging.getLogger('leetchi')


class NewWithdrawalForm(WithdrawalForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(NewWithdrawalForm, self).__init__(*args, **kwargs)

    def save(self):
        try:
            w = LeetchiWithdrawal()
            for field_name in ('bank_account_bic', 'bank_account_iban',
                               'bank_account_owner_address', 'bank_account_owner_name',
                               'amount', 'client_fee_amount'):
                setattr(w, field_name, self.cleaned_data[field_name])

            payer, created = self.user.get_profile().get_payer()

            w.user = payer
            w.save(handler)

            withdrawal = Withdrawal()
            withdrawal.withdrawal = w
            withdrawal.content_object = self.user
            withdrawal.save()

        except (APIError, DecodeError, AssertionError, AttributeError), e:
            logger_leetchi.error(e)
            return False
        else:
            return withdrawal


class NewContributionForm(forms.Form):
    amount = forms.CharField(label=_("Amount"), widget=forms.TextInput, help_text=_('Value in decimal, e.g. 20.50e'))

    def save(self, request, user, return_url, template_url=None):
        try:
            current_site = Site.objects.get_current()

            protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")

            absolute_url = request.META.get('HTTP_HOST', current_site.domain)

            return_url = u"%s://%s%s" % (
                protocol,
                unicode(absolute_url),
                return_url
            )

            contribution = Contribution()
            contribution.content_object = user
            contribution.user = request.user
            contribution.wallet_id = 0
            contribution.amount = int(float(self.cleaned_data.get('amount')) * 100)
            contribution.return_url = return_url

            if waffle.flag_is_active(request, 'payment_template_url') and template_url:
                template_url = u"https://%s%s" % (
                    unicode(absolute_url),
                    template_url
                )

                contribution.template_url = template_url

            contribution.save(user=user)
        except (APIError, DecodeError, AssertionError, AttributeError), e:
            logger_leetchi.error(e)
            return False
        else:
            return contribution


class NewTransferForm(forms.Form):
    amount = forms.CharField(label=_("Amount"), widget=forms.TextInput, help_text=_('Value in decimal, e.g. 20.50e'))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(NewTransferForm, self).__init__(*args, **kwargs)

    def clean_amount(self):

        leetchi_user, created = self.user.get_profile().get_payer()

        amount = self.cleaned_data.get('amount')

        if not self.is_personal_amount_enough(amount):
            raise forms.ValidationError(_('Your personal amount %(personal_amount)s is not enough to make this transfer %(amount)s' % {
                'personal_amount': leetchi_user.personal_wallet_amount_converted,
                'amount': amount
            }))

        return amount

    def is_personal_amount_enough(self, amount):
        leetchi_user, created = self.user.get_profile().get_payer()

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
        except (APIError, DecodeError, AssertionError, AttributeError), e:
            logger_leetchi.error(e)
            return False
        else:
            return transfer
