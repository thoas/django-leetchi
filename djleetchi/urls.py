from django.conf.urls import patterns, url
from django.contrib.admin.views.decorators import staff_member_required

from djleetchi.views import (ContributionDetailView, WalletDetailView, RefundDetailView,
                             TransferDetailView, TransferRefundDetailView, WithdrawalDetailView)

urlpatterns = patterns(
    '',
    url(r'^wallet/detail/(?P<wallet_id>\d+)/$',
        staff_member_required(WalletDetailView.as_view()),
        name='leetchi_wallet_detail'),

    url(r'^contribution/detail/(?P<contribution_id>\d+)/$',
        staff_member_required(ContributionDetailView.as_view()),
        name='leetchi_contribution_detail'),

    url(r'^refund/detail/(?P<refund_id>\d+)/$',
        staff_member_required(RefundDetailView.as_view()),
        name='leetchi_refund_detail'),

    url(r'^transfer/detail/(?P<transfer_id>\d+)/$',
        staff_member_required(TransferDetailView.as_view()),
        name='leetchi_transfer_detail'),

    url(r'^transferrefund/detail/(?P<transferrefund_id>\d+)/$',
        staff_member_required(TransferRefundDetailView.as_view()),
        name='leetchi_transferrefund_detail'),

    url(r'^withdrawal/detail/(?P<withdrawal_id>\d+)/$',
        staff_member_required(WithdrawalDetailView.as_view()),
        name='leetchi_withdrawal_detail'),
)
