# -*- coding: utf-8 -*-
from django.views.generic.base import View
from django.http import HttpResponseServerError, Http404

from leetchi import resources
from leetchi.base import DoesNotExist as ResourceDoesNotExist

from .api import handler
from .http import JSONResponse
from .encoders import JSONEncoder


class BaseResourceDetailView(View):
    def get(self, request, *args, **kwargs):

        resource_id = int(kwargs.get(self.resource_id))

        try:
            resource = self.resource_class.get(resource_id, handler)
        except ResourceDoesNotExist:
            raise Http404
        else:
            if resource:
                data = dict((attribute, getattr(resource, attribute))
                            for attribute in self.attributes)

            return JSONResponse(data, cls=JSONEncoder)

        return HttpResponseServerError("Error")


class ContributionDetailView(BaseResourceDetailView):
    resource_class = resources.Contribution
    resource_id = 'contribution_id'
    attributes = ('is_succeeded', 'is_completed', 'creation_date',
                  'update_date', 'amount', 'id', 'error')


class WalletDetailView(BaseResourceDetailView):
    resource_class = resources.Wallet
    resource_id = 'wallet_id'
    attributes = ('name', 'spent_amount', 'amount',
                  'collected_amount', 'remaining_amount', 'is_closed')


class RefundDetailView(BaseResourceDetailView):
    resource_class = resources.Refund
    resource_id = 'refund_id'
    attributes = ('creation_date', 'update_date', 'user_id',
                  'contribution_id', 'is_succeeded', 'is_completed', 'error')


class TransferDetailView(BaseResourceDetailView):
    resource_class = resources.Transfer
    resource_id = 'transfer_id'
    attributes = ('creation_date', 'update_date', 'payer_id',
                  'beneficiary_id', 'amount', 'payer_wallet_id', 'beneficiary_wallet_id')


class TransferRefundDetailView(BaseResourceDetailView):
    resource_class = resources.TransferRefund
    resource_id = 'transferrefund_id'
    attributes = ('transfer_id', 'user_id', 'creation_date', 'update_date')


class WithdrawalDetailView(BaseResourceDetailView):
    resource_id = 'withdrawal_id'
    resource_class = resources.Withdrawal
    attributes = ('creation_date', 'update_date', 'user_id', 'amount', 'client_fee_amount',
                  'wallet_id', 'is_succeeded', 'is_completed', 'error', 'bank_account_owner_name',
                  'bank_account_owner_address', 'bank_account_iban', 'bank_account_bic')
