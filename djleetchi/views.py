# -*- coding: utf-8 -*-
import logging
import datetime

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.views.generic.base import View
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, Http404

from leetchi.exceptions import APIError, DecodeError
from leetchi.resources import (Contribution as LeetchiContribution,
                               Refund as LeetchiRefund,
                               Wallet as LeetchiWallet,
                               Withdrawal as LeetchiWithdrawal,
                               Transfer as LeetchiTransfer,
                               TransferRefund as LeetchiTransferRefund)

from leetchi.base import DoesNotExist as ResourceDoesNotExist

from djleetchi import handler
from djleetchi.models import Contribution, Transfer, Refund, TransferRefund

import waffle

import partners

from partners.models import Partner

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

logger_leetchi = logging.getLogger('leetchi')


class PaymentViewMixin(object):
    def get(self, request, *args, **kwargs):
        user = request.user

        if not self.get_object().is_credit_card_payment_allowed():
            messages.error(request, _(u'Il n\'est pas possible de payer par carte bancaire'))

            return self.redirect_not_allowed()

        try:
            leetchi_user, created = user.get_profile().get_payer()

            leetchi_wallet, created = self.get_object().get_wallet()

            if not leetchi_user or not leetchi_wallet or not leetchi_wallet.get_pk():
                raise AttributeError

            personal_wallet_amount = leetchi_user.personal_wallet_amount or 0

            amount = int(self.get_amount() * 100)

            if amount > personal_wallet_amount:
                protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")

                absolute_url = request.META.get('HTTP_HOST', partners.get_site().domain)

                return_url = u"%s://%s%s" % (
                    protocol,
                    unicode(absolute_url),
                    self.get_return_url()
                )

                real_amount = amount - personal_wallet_amount

                contribution = Contribution()
                contribution.content_object = self.get_observed()
                contribution.user = self.request.user
                contribution.wallet_id = 0
                contribution.amount = real_amount
                contribution.return_url = return_url
                contribution.type = self.get_type()
                contribution.culture = get_current_lang()

                if waffle.flag_is_active(request, 'payment_template_url') and self.get_type() == CONTRIBUTION_TYPE_CHOICES.PAYLINE:
                    try:
                        absolute_url = Partner.objects.get_default().site.domain
                    except Partner:
                        pass

                    template_url = u"https://%s%s" % (
                        unicode(absolute_url),
                        self.get_template_url()
                    )

                    contribution.template_url = template_url

                contribution.save()

                return self.success(contribution)

            return HttpResponseRedirect(self.get_return_url())

        except (APIError, DecodeError, AssertionError, AttributeError), e:
            logger_leetchi.error(e)
            messages.error(request, _(u'Problème de connexion au système bancaire, merci de réessayer dans quelques minutes'))

            return self.redirect_not_allowed()

    def success(self, contribution):
        return HttpResponseRedirect(contribution.contribution.payment_url)

    def get_template_url(self):
        return reverse('payment_form', kwargs={
            'partner_id': partners.get_current().pk,
            'lang': get_current_lang()
        })


class PaymentDoneViewMixin(object):

    def get(self, request, *args, **kwargs):

        try:
            contribution_id = request.GET.get('ContributionID', None)

            if contribution_id:
                contribution_id = int(contribution_id)

                try:
                    contribution = Contribution.objects.get(contribution=contribution_id)
                except Contribution.DoesNotExist:
                    pass
                else:

                    leetchi_contribution = contribution.contribution

                    if leetchi_contribution.is_success():
                        contribution.is_success = True
                        contribution.is_completed = True

                        contribution.save()

                    elif leetchi_contribution.is_completed and not leetchi_contribution.is_succeeded:
                        contribution.is_success = False
                        contribution.is_completed = True

                        contribution.save()

                        return HttpResponseRedirect(self.get_error_url(leetchi_contribution))

            leetchi_user, created = request.user.get_profile().get_payer()

            leetchi_wallet, created = self.get_object().get_wallet()

            if not leetchi_user or not leetchi_wallet or not leetchi_wallet.get_pk():
                raise AttributeError

            personal_amount = leetchi_user.personal_wallet_amount

            amount = int(self.get_amount() * 100)

            if personal_amount < amount:
                return self.redirect_payment_error(request)

            transfer = Transfer()
            transfer.content_object = self.get_observed()
            transfer.amount = amount
            transfer.payer = self.request.user
            transfer.beneficiary = self.get_object().owner
            transfer.beneficiary_wallet = leetchi_wallet
            transfer.save()

        except (APIError, DecodeError, AttributeError), e:
            logger_leetchi.error(e)

            return self.redirect_payment_error(request)

        else:
            return self.success()

    def redirect_payment_error(self, request):
        messages.error(request, _(u'Problème de connexion au système bancaire, impossible de transferer votre donation. Merci de réessayer dans quelques minutes ou annuler votre paiement sur votre porte monnaie electronique <a href="%(transactions_url)s">ici</a>') % {
            'transactions_url': reverse('account_transactions', kwargs={
                'slug': request.user.username
            })
        })

        return self.redirect_not_allowed()


class RefundViewMixin(object):
    def is_valid(self):
        return True

    def error(self):
        pass

    def extra(self):
        return {}

    def success(self):
        pass

    def get_statuses(self, obj):
        statuses = {}

        resources = (
            (Refund, [{'user': self.user, 'is_success': True, 'is_completed': True}, {'user': self.user, 'is_completed': False}]),
            (TransferRefund, [{'user': self.user}],),
            (Contribution, [{'is_success': True, 'user': self.user}],),
            (Transfer, [{'payer': self.user}],)
        )

        for model_class, extra_list in resources:

            q_object = None

            for extra in extra_list:
                parameters = dict({
                    'object_id': obj.pk,
                    'content_type': self.contenttype,
                }, **extra)

                current_filter = models.Q(**parameters)

                if q_object:
                    q_object |= current_filter
                else:
                    q_object = current_filter

            results = model_class.objects.filter(q_object)

            if len(results):
                statuses[model_class._meta.verbose_name] = results

        return statuses

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        context = self.get_context_data(object=self.object)

        self.user = self.get_user()

        self.contenttype = ContentType.objects.get_for_model(self.get_observed())

        self.statuses = self.get_statuses(self.get_observed())

        response = self.validate()

        if response and isinstance(response, HttpResponse):
            return response

        context['statuses'] = self.statuses

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        self.get_context_data(object=self.object)

        self.user = self.get_user()

        self.contenttype = ContentType.objects.get_for_model(self.get_observed())

        self.statuses = self.get_statuses(self.get_observed())

        response = self.validate()

        if response and isinstance(response, HttpResponse):
            return response

        try:
            leetchi_user = self.get_user().get_profile().leetchi_user

            if not leetchi_user or not leetchi_user.get_pk():
                self.error_message()
            else:

                if 'transfer' in self.statuses and not 'transferrefund' in self.statuses:
                    transfers = self.statuses.get('transfer')

                    transfer_refund_list = []

                    for transfer in transfers:
                        transfer_refund = TransferRefund()
                        transfer_refund.content_object = self.get_observed()
                        transfer_refund.transfer = transfer
                        transfer_refund.user = self.user
                        transfer_refund.save()

                        transfer_refund_list.append(transfer_refund)

                    return self.success(transfer_refund_list)

                elif 'contribution' in self.statuses and not 'refund' in self.statuses:

                    contributions = self.statuses.get('contribution')

                    refund_list = []

                    for contribution in contributions:
                        refund = Refund()
                        refund.content_object = self.get_observed()
                        refund.contribution = contribution
                        refund.user = self.user
                        refund.save()

                        refund_list.append(refund)

                    return self.success(refund_list)

        except (DecodeError, APIError), e:
            logger_leetchi.error(e)
            self.error_message()

        return HttpResponseRedirect(self.get_return_url())

    def error_message(self):
        messages.error(self.request, _(u'Problème de connexion au système bancaire, merci de réessayer dans quelques minutes'))


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

contribution_detail = ContributionDetailView.as_view()


class WalletDetailView(BaseResourceDetailView):
    resource_class = LeetchiWallet
    resource_id = 'wallet_id'
    attributes = ('name', 'spent_amount', 'amount',
                  'collected_amount', 'remaining_amount', 'is_closed')

wallet_detail = WalletDetailView.as_view()


class RefundDetailView(BaseResourceDetailView):
    resource_class = LeetchiRefund
    resource_id = 'refund_id'
    attributes = ('creation_date', 'update_date', 'user_id',
                  'contribution_id', 'is_succeeded', 'is_completed', 'error')

refund_detail = RefundDetailView.as_view()


class TransferDetailView(BaseResourceDetailView):
    resource_class = LeetchiTransfer
    resource_id = 'transfer_id'
    attributes = ('creation_date', 'update_date', 'payer_id',
                  'beneficiary_id', 'amount', 'payer_wallet_id', 'beneficiary_wallet_id')

transfer_detail = TransferDetailView.as_view()


class TransferRefundDetailView(BaseResourceDetailView):
    resource_class = LeetchiTransferRefund
    resource_id = 'transferrefund_id'
    attributes = ('transfer_id', 'user_id', 'creation_date', 'update_date')

transferrefund_detail = TransferRefundDetailView.as_view()


class WithdrawalDetailView(BaseResourceDetailView):
    resource_id = 'withdrawal_id'
    resource_class = LeetchiWithdrawal
    attributes = ('creation_date', 'update_date', 'user_id', 'amount', 'client_fee_amount',
                  'wallet_id', 'is_succeeded', 'is_completed', 'error', 'bank_account_owner_name',
                  'bank_account_owner_address', 'bank_account_iban', 'bank_account_bic')

withdrawal_detail = WithdrawalDetailView.as_view()
