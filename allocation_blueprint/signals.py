from django.dispatch import receiver
from django_q.tasks import async_task

from coldfront.core.allocation.signals import allocation_new


@receiver(allocation_new)
def apply_blueprint(sender, **kwargs):
    allocation_pk = kwargs.get("allocation_pk")
    async_task("allocation_blueprint.tasks.apply_blueprint", allocation_pk)
