import collections
import datetime

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import Group


def start_default():
    return datetime.datetime.now()


def expire_default():
    return datetime.datetime.now() + datetime.timedelta(days=14)


class MessageManager(models.Manager):
    def create_message(self, subject, body, users=None, groups=None,
                       expires=True, **kwargs):
        """
        Create a message for one or more users.
        If users is provided but not groups, just those users will receive
        the message. If groups is provided but not users, all members of that
        group, past, current, and future, should see it. If both are provided,
        all group members as well as the specified users (even if they are not
        group members) will get the message.

        Inputs:
        :subject: Subject title for message being created
        :body: Body text of the message to be created
        :users: List of users to add this message to; :users:, :groups:, or
            both must be provided
        :groups: List of groups whose members should see this message; :users:,
            :groups:, or both must be provided
        :expires: Will this message have an expiration date, default: True
        :kwargs: Other fields from the Message model, all optional
        """
        kwargs.setdefault('message_type', 'error')

        if not expires:
            # Message should not expire; ensure expire_at is not going to be
            # set by the caller
            kwargs['expire_at'] = None

        if groups is None and users is None:
            raise ValueError("users and/or groups must have a value")

        message = self.create(subject=subject, body=body, **kwargs)

        if groups is not None:
            if not isinstance(groups, collections.Iterable):
                groups = [groups]
            for group in groups:
                message.group.add(group)

        if users is not None:
            # Users are associated with messages via the MessageInfo through
            # table. If we are going to add users, we need to add entries to
            # the through table for them.
            if not isinstance(users, collections.Iterable):
                users = [users]

            for user in users:
                MessageInfo.objects.create(user=user, message=message)

        return message


class Message(models.Model):
    """
    Message
    """
    TYPE_OF_MESSAGES = (
        ('error', 'Error'),
        ('info', 'Info'),
        ('block', 'Notice'),
        ('success', 'Success'),
    )
    group = models.ManyToManyField(Group)
    users = models.ManyToManyField('usermodel.User', through='MessageInfo')
    subject = models.CharField("Subject", max_length=200)
    message_type = models.CharField("Message type", choices=TYPE_OF_MESSAGES,
                                    max_length=200)
    body = models.TextField('Body')
    start_on = models.DateTimeField('Start on', default=start_default)
    expire_at = models.DateTimeField('Expire at',
                                     db_index=True,
                                     default=expire_default,
                                     null=True,
                                     help_text="Default is two weeks " +
                                               "after message is sent.")
    btn_text = models.CharField('Button text', max_length=100, default='OK')
    system = models.BooleanField('System message', default=False,
                                 help_text='This is a system message and '
                                           'appears as an alert as well as '
                                           'in the inbox.')

    objects = MessageManager()

    @property
    def display_type(self):
        """
        Returns the tooltip for this message on the inbox.
        """
        return dict(self.TYPE_OF_MESSAGES).get(self.message_type,
                                               self.message_type.title())

    def __unicode__(self):
        return self.subject


class MessageInfo(models.Model):
    """
    Through model for Message.
    """
    user = models.ForeignKey('usermodel.User')
    message = models.ForeignKey(Message)
    read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField('read at', null=True)
    expired = models.BooleanField(default=False, db_index=True)
    expired_on = models.DateTimeField('expired on', null=True)
    deleted_on = models.DateTimeField('deleted on', blank=True, null=True,
                                      db_index=True)

    class Meta:
        unique_together = (('user', 'message'), )

    def __unicode__(self):
        return self.message.subject

    def is_unread(self):
        return bool(self.read_at is None)

    def mark_unread(self):
        self.read = False
        self.read_at = None
        self.save()

    def mark_read(self):
        self.read = True
        self.read_at = datetime.datetime.now()
        self.save()

    def mark_expired(self):
        self.read = False
        self.expired = True
        self.expired_on = datetime.datetime.now()
        self.save()

    def expired_time(self):
        message = self.message
        if message.expire_at is None:
            return False
        now = timezone.now()
        if timezone.is_naive(self.message.expire_at):
            message.expire_at = timezone.make_aware(
                message.expire_at, timezone.UTC())
        if timezone.is_naive(self.message.start_on):
            message.start_on = timezone.make_aware(
                message.start_on, timezone.UTC())
        date_expired = (message.expire_at - message.start_on) + \
            message.start_on
        if now > date_expired:
            self.mark_expired()
            return True
        else:
            return False