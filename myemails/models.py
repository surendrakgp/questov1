from datetime import datetime

from django.contrib.auth.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.template import Template, Context

from seo.models import CompanyUser
# import tasks


class EmailSection(models.Model):
    SECTION_TYPES = (
        (1, 'Header'),
        (3, 'Footer'),
    )

    name = models.CharField(max_length=255)
    owner = models.ForeignKey('seo.Company', blank=True, null=True)
    section_type = models.PositiveIntegerField(choices=SECTION_TYPES)
    content = models.TextField()

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.owner or "Global")


class EmailTemplate(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey('seo.Company', blank=True, null=True)
    header = models.ForeignKey('EmailSection', related_name='header_for')
    body = models.TextField()
    footer = models.ForeignKey('EmailSection', related_name='footer_for')
    event = models.ForeignKey('Event', null=True)
    is_active = models.BooleanField('IsActive', default=False)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.owner or "Global")

    @staticmethod
    def build_context(for_object):
        """
        Builds context based on a generic number of things that
        a user might want to include in an email.

        Inputs:
        :for_object: The object the context is being built for.
        :return: A dictionary of context for the templates to use.

        """
        context = for_object.context()
        return Context(context)

    def render(self, for_object):
        """
        Renders the EmailTemplate for a given object.

        Inputs:
        :for_object: The object the email is being rendered for.
        :return: The rendered email.
        """
        context = self.build_context(for_object)
        template = Template('\n'.join([self.header.content, self.body,
                                       self.footer.content]))
        return template.render(context)


class Event(models.Model):
    is_active = models.BooleanField(default=True)
    owner = models.ForeignKey('seo.Company')
    sites = models.ManyToManyField('seo.SeoSite')
    name = models.CharField(max_length=255)
    model = models.ForeignKey(ContentType)
    description = models.TextField()

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.owner)

    # def schedule_task(self, for_object):
    #     """
    #     Creates an EmailTask for the for_object.

    #     Inputs:
    #     :for_object: The object that will have an email sent for it
    #                  in the future.

    #     Returns:
    #     :return: The created EamilTask.
    #     """
    #     return EmailTask.objects.create(
    #         act_on=for_object,
    #         related_event=self,
    #         scheduled_for=self.schedule_for(for_object)
    #     )

    def schedule_for(self, for_object):
        """
        Determines what time an event should be scheduled for; Unless
        overridden in a subclass, this defaults to right now.

        Inputs:
        :for_object: Object being scheduled; not used in the default method.

        Returns:
        :return: Time to schedule an event.
        """
        return datetime.now()

    def send_email(self, for_object):
        """
        Sends an email for a for_object.

        Inputs:
        :for_object: The object an email is being sent for.
        """
        subject = ''
        if self.model.model == 'purchasedjob':
            # host company to purchaser
            recipient_company = for_object.owner
            sending_company = for_object.purchased_product.product.owner
        elif self.model.model == 'purchasedproduct':
            # host company to purchaser
            recipient_company = for_object.owner
            sending_company = for_object.product.owner
        elif self.model.model == 'request':
            # purchaser to host company
            recipient_company = for_object.owner
            sending_company = for_object.requesting_company()
            subject = '%s has submitted a new request' % sending_company.name
        elif self.model.model == 'invoice':
            # host company to purchaser
            recipient_company = for_object.purchasedproduct_set.first()\
                .product.owner
            sending_company = for_object.owner
            subject = 'Your invoice from %s' % sending_company.name
        else:
            raise NotImplementedError('Add %s here somewhere!' %
                                      self.model.model)

        if not subject:
            subject = 'An update on your %s' % self.model.name

        recipients = CompanyUser.objects.filter(
            company=recipient_company).values_list('user__email',
                                                   flat=True)
        if hasattr(sending_company, 'companyprofile'):
            email_domain = sending_company.companyprofile.outgoing_email_domain
        else:
            email_domain = 'my.jobs'

        template = self.active_template()
        if template is not None:
            body = template.render(for_object)
            send_mail(subject, body, '%s@%s' %
                      (self.model.model, email_domain),
                      recipients)

    def active_template(self):
        return EmailTemplate.objects.filter(event=self, is_active=True).first()


class EmailTask(models.Model):
    # Object being used to generate this email
    object_id = models.PositiveIntegerField()
    object_model = models.ForeignKey(ContentType, related_name='email_model')
    act_on = GenericForeignKey('object_model', 'object_id')

    # Event type of this email
    event_id = models.PositiveIntegerField()
    event_model = models.ForeignKey(ContentType, related_name='email_type')
    related_event = GenericForeignKey('event_model', 'event_id')

    completed_on = models.DateTimeField(blank=True, null=True)

    scheduled_for = models.DateTimeField(default=datetime.now)
    scheduled_at = models.DateTimeField(auto_now_add=True)

    task_id = models.CharField(max_length=36, blank=True, default='',
                               help_text='guid with dashes')

    @property
    def completed(self):
        return bool(self.completed_on)

    def schedule(self):
        """
        Submits this task to Celery for processing.
        """
        # tasks.send_event_email.apply_async(args=[self], eta=self.scheduled_for)

    def send_email(self):
        self.related_event.send_email(self.act_on)


def event_receiver(signal, content_type, type_):
    def event_receiver_decorator(fn):
        sender = ContentType.objects.get(model=content_type).model_class()
        dispatch_uid = '%s_%s_%s' % (fn.__name__, content_type, type_)
        wrapper = receiver(signal, sender=sender, dispatch_uid=dispatch_uid)
        return wrapper(fn)
    return event_receiver_decorator


# I don't really like doing it this way (get from database pre save, set
# attribute, get again post save), but we need to be able to 1) determine what
# was changed and 2) only send an email if the save is successful. - TP

@event_receiver(pre_save, 'invoice', 'created')
@event_receiver(pre_save, 'purchasedproduct', 'created')
def pre_add_invoice(sender, instance, **kwargs):
    """
    Determines if an invoice has been added to the provided instance.

    Inputs:
    :sender: Which event type is being saved
    :instance: Specific instance being saved
    """
    invoice_added = hasattr(instance, 'invoice')
    if instance.pk:
        original = sender.objects.get(pk=instance.pk)
        invoice_added = not hasattr(original, 'invoice') and invoice_added
    instance.invoice_added = invoice_added


@event_receiver(post_save, 'invoice', 'created')
@event_receiver(post_save, 'purchasedproduct', 'created')
def post_add_invoice(sender, instance, **kwargs):
    """
    Schedules tasks for the instance if pre_add_invoice determined that an
    invoice was added.

    Inputs:
    :sender: Which event type is being saved
    :instance: Specific instance being saved
    """
    if instance.invoice_added:
        content_type = ContentType.objects.get(model='invoice')
        events = Event.objects.filter(model=content_type,
                                      owner=instance.product.owner)
        for event in events:
            EmailTask.objects.create(act_on=instance.invoice,
                                     related_event=event).schedule()
