from celery.task import PeriodicTask, task
from celery import group

from leetchi.exceptions import APIError, DecodeError

from datetime import timedelta


class SyncContributionsTask(PeriodicTask):
    run_every = timedelta(minutes=25)

    def run(self, **kwargs):
        from djleetchi.models import Contribution

        contributions = Contribution.objects.filter(is_completed=False).values_list('id')

        tasks = [sync_contribution.subtask(args=(c[0], )) for c in contributions]

        job = group(tasks)

        result = job.apply_async()

        return result


@task
def sync_contribution(contribution_id):
    from djleetchi.models import Contribution

    logger = sync_contribution.get_logger()

    try:

        c = Contribution.objects.get(pk=contribution_id)

        contribution = c.contribution

        if contribution:
            if contribution.is_completed:
                if contribution.is_succeeded:
                    logger.info(u'[Contribution]: set succeeded for %d, from leetchi contribution %d' %
                                (c.pk, c.contribution_id))
                    c.is_success = True
                else:
                    logger.info(u'[Contribution]: set aborted for %d, from leetchi contribution %d' %
                                (c.pk, c.contribution_id))
                    c.is_success = False

                c.is_completed = True
                c.save()
            else:
                logger.info(u'[Contribution]: do nothing for %d, from leetchi contribution %d' %
                            (c.pk, c.contribution_id))
        else:
            logger.info(u'[Contribution]: can\'t reach n.%d' % (c.contribution_id))

    except (APIError, DecodeError, Contribution.DoesNotExist), e:
        logger.error(e)


class SyncRefundsTask(PeriodicTask):
    run_every = timedelta(minutes=25)

    def run(self, **kwargs):
        from djleetchi.models import Refund

        refunds = Refund.objects.filter(is_completed=False).values_list('id')

        tasks = [sync_refund.subtask(args=(c[0], )) for c in refunds]

        job = group(tasks)

        result = job.apply_async()

        return result


@task
def sync_refund(refund_id):
    from djleetchi.models import Refund

    logger = sync_refund.get_logger()

    r = Refund.objects.get(pk=refund_id)

    try:
        refund = r.refund

        if refund:
            if refund.is_completed:
                if refund.is_succeeded:
                    logger.info(u'[Refund]: set succeeded for %d, from leetchi refund %d' %
                                (r.pk, r.refund_id))
                    r.is_success = True

                    contribution = r.contribution
                else:
                    logger.info(u'[Refund]: set aborted for %d, from leetchi refund %d' %
                                (r.pk, r.refund_id))
                    r.is_success = False

                r.is_completed = True
                r.save()
            else:
                logger.info(u'[Refund]: do nothing for %d, from leetchi refund %d' %
                            (r.pk, r.refund_id))
        else:
            logger.info(u'[Refund]: can\'t reach n.%d' % (r.refund_id))

    except (APIError, DecodeError), e:
        logger.error(e)


@task
def sync_resource(klass, resource_id):
    try:
        instance = klass.objects.get(pk=resource_id)
    except klass.DoesNotExist:
        logger.error(u'Resource %s with id %s does not exists' %
                     (klass.__name__, resource_id))
    else:
        try:
            instance.sync()
        except (APIError, DecodeError) as exc:
            logger.error(exc)

            raise sync_resource.retry(exc=exc, countdown=60)
