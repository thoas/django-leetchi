# -*- coding: utf-8 -*-
import datetime

from django.views.generic.base import View
from django.http import HttpResponseServerError, Http404

from leetchi.resources import (Contribution as LeetchiContribution,
                               Refund as LeetchiRefund,
                               Wallet as LeetchiWallet,
                               Withdrawal as LeetchiWithdrawal,
                               Transfer as LeetchiTransfer,
                               TransferRefund as LeetchiTransferRefund)

from leetchi.base import DoesNotExist as ResourceDoesNotExist

from djleetchi import handler
from djleetchi.util import JSONResponse


try:
    import simplejson as json
except ImportError:
    import json


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return '\n'.join([u'%s: %s' % (k, v) for k, v in obj.iteritems()])
        return json.JSONEncoder.default(self, obj)


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
    resource_class = LeetchiContribution
    resource_id = 'contribution_id'
    attributes = ('is_succeeded', 'is_completed', 'creation_date',
                  'update_date', 'amount', 'id', 'error')


class WalletDetailView(BaseResourceDetailView):
    resource_class = LeetchiWallet
    resource_id = 'wallet_id'
    attributes = ('name', 'spent_amount', 'amount',
                  'collected_amount', 'remaining_amount', 'is_closed')


class RefundDetailView(BaseResourceDetailView):
    resource_class = LeetchiRefund
    resource_id = 'refund_id'
    attributes = ('creation_date', 'update_date', 'user_id',
                  'contribution_id', 'is_succeeded', 'is_completed', 'error')


class TransferDetailView(BaseResourceDetailView):
    resource_class = LeetchiTransfer
    resource_id = 'transfer_id'
    attributes = ('creation_date', 'update_date', 'payer_id',
                  'beneficiary_id', 'amount', 'payer_wallet_id', 'beneficiary_wallet_id')


class TransferRefundDetailView(BaseResourceDetailView):
    resource_class = LeetchiTransferRefund
    resource_id = 'transferrefund_id'
    attributes = ('transfer_id', 'user_id', 'creation_date', 'update_date')


class WithdrawalDetailView(BaseResourceDetailView):
    resource_id = 'withdrawal_id'
    resource_class = LeetchiWithdrawal
    attributes = ('creation_date', 'update_date', 'user_id', 'amount', 'client_fee_amount',
                  'wallet_id', 'is_succeeded', 'is_completed', 'error', 'bank_account_owner_name',
                  'bank_account_owner_address', 'bank_account_iban', 'bank_account_bic')
