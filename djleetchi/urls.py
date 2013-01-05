from django.conf.urls import patterns, url
from django.contrib.admin.views.decorators import staff_member_required

from djleetchi.views import (contribution_detail,
                             wallet_detail,
                             refund_detail,
                             withdrawal_detail,
                             transferrefund_detail,
                             transfer_detail)

urlpatterns = patterns(
    '',
    url(r'^wallet/detail/(?P<wallet_id>\d+)/$',
        staff_member_required(wallet_detail),
        name='leetchi_wallet_detail'),

    url(r'^contribution/detail/(?P<contribution_id>\d+)/$',
        staff_member_required(contribution_detail),
        name='leetchi_contribution_detail'),

    url(r'^refund/detail/(?P<refund_id>\d+)/$',
        staff_member_required(refund_detail),
        name='leetchi_refund_detail'),

    url(r'^transfer/detail/(?P<transfer_id>\d+)/$',
        staff_member_required(transfer_detail),
        name='leetchi_transfer_detail'),

    url(r'^transferrefund/detail/(?P<transferrefund_id>\d+)/$',
        staff_member_required(transferrefund_detail),
        name='leetchi_transferrefund_detail'),

    url(r'^withdrawal/detail/(?P<withdrawal_id>\d+)/$',
        staff_member_required(withdrawal_detail),
        name='leetchi_withdrawal_detail'),
)
