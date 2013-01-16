import logging

from django.shortcuts import redirect
from django.http import HttpResponse
from django.db import models
from django.contrib.contenttypes.models import ContentType

from leetchi.exceptions import APIError, DecodeError

from djleetchi.models import Contribution, Transfer, Refund, TransferRefund
from djleetchi.util import get_current_lang
from djleetchi.helpers import get_payer, get_wallet

logger_leetchi = logging.getLogger('leetchi')


class PaymentViewMixin(object):
    def get(self, request, *args, **kwargs):
        user = request.user

        try:
            leetchi_user = get_payer(user)

            leetchi_wallet = get_wallet(self.get_object())

            if not leetchi_user or not leetchi_wallet or not leetchi_wallet.get_pk():
                raise AttributeError

            personal_wallet_amount = leetchi_user.personal_wallet_amount or 0

            amount = int(self.get_amount() * 100)

            if amount > personal_wallet_amount:
                return_url = self.get_return_url()

                real_amount = amount - personal_wallet_amount

                contribution = Contribution()
                contribution.content_object = self.get_observed()
                contribution.user = self.request.user
                contribution.wallet_id = 0
                contribution.amount = real_amount
                contribution.return_url = return_url
                contribution.type = self.get_type()
                contribution.culture = get_current_lang()

                template_url = self.get_template_url()

                if template_url:
                    contribution.template_url = template_url

                contribution.save()

                return redirect(self.get_success_url(contribution))

            return redirect(self.get_return_url())

        except (APIError, DecodeError, AssertionError, AttributeError), e:
            logger_leetchi.error(e)

            return redirect(self.get_error_url())

    def get_success_url(self, contribution):
        return contribution.contribution.payment_url

    def get_template_url(self):
        return None

    def get_return_url(self):
        raise NotImplementedError

    def get_observed(self):
        raise NotImplementedError


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

                        return redirect(self.get_error_url(leetchi_contribution))

            leetchi_user = get_payer(request.user)

            leetchi_wallet = get_wallet(self.get_object())

            if not leetchi_user or not leetchi_wallet or not leetchi_wallet.get_pk():
                raise AttributeError

            personal_amount = leetchi_user.personal_wallet_amount

            amount = int(self.get_amount() * 100)

            if personal_amount < amount:
                return self.redirect_payment_error(request)

            transfer = Transfer()
            transfer.content_object = self.get_observed()
            transfer.amount = amount
            transfer.payer = self.get_payer()
            transfer.beneficiary = self.get_beneficiary()
            transfer.beneficiary_wallet = leetchi_wallet
            transfer.save()

        except (APIError, DecodeError, AttributeError), e:
            logger_leetchi.error(e)

            return redirect(self.get_payment_error_url())
        else:
            return redirect(self.get_success_url())

    def get_payment_error_url(self):
        raise NotImplementedError

    def get_success_url(self):
        raise NotImplementedError

    def get_beneficiary(self):
        raise NotImplementedError

    def get_payer(self):
        raise NotImplementedError

    def get_observed(self):
        raise NotImplementedError


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
            leetchi_user = get_payer(self.get_user())

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

        return redirect(self.get_return_url())
