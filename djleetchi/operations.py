from django.db import models
from django.contrib.contenttypes.models import ContentType

from djleetchi.models import TransferRefund, Transfer, Contribution, Refund
from djleetchi.helpers import queryset_to_dict


def transfer_refund(instance, user):
    contenttype = ContentType.objects.get_for_model(instance)

    transfers = Transfer.objects.filter(object_id=instance.pk, content_type=contenttype)

    transfer_refund_list = []

    if len(transfers):
        for transfer in transfers:
            transfer_refund = TransferRefund()
            transfer_refund.content_object = instance
            transfer_refund.transfer = transfer
            transfer_refund.user = user
            transfer_refund.save()

            transfer_refund_list.append(transfer_refund)

        return transfer_refund_list

    return False


def refund(instance, user):
    contenttype = ContentType.objects.get_for_model(instance)

    contributions = Contribution.objects.filter(object_id=instance.pk, content_type=contenttype,
                                                is_success=True, is_completed=True)

    refunds = queryset_to_dict((Refund.objects.filter(contribution__in=[contribution.pk for contribution in contributions])
                                .filter(models.Q(is_success=True, is_completed=True) | models.Q(is_success=False, is_completed=False))),
                               key='contribution_id', singular=False)

    refund_list = []

    if len(contributions):
        for contribution in contributions:
            if not contribution.pk in refunds:
                refund = Refund()
                refund.content_object = instance
                refund.contribution = contribution
                refund.user = user
                refund.save()

                refund_list.append(transfer_refund)

        return refund_list

    return False
