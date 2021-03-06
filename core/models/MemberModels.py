import os

from core.models.fields.PrimaryKeyField import PrimaryKeyField
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group, Permission, PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.urls import reverse
from django.utils.timezone import datetime, now, timedelta
from ExCSystem import settings
from phonenumber_field.modelfields import PhoneNumberField

from .CertificationModels import Certification
from .fields.RFIDField import RFIDField


def get_profile_pic_upload_location(instance, filename):
    """Save profile pictures in object store"""
    extension = filename.split('.')[-1]

    # Get the name with all special characters removed
    name_str = ''.join(e for e in instance.get_full_name() if e.isalnum())
    year = datetime.now().year

    # Assemble file location and insert date data
    location = f'ProfilePics/{year}/{name_str}.{extension}'
    location = datetime.strftime(datetime.now(), location)
    return location


class MemberManager(BaseUserManager):
    def create_member(self, email, rfid, membership_duration, password=None):
        """
        Creates and saves a Member with the given email, date of
        birth and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        # Trying to add the max timedelta to now results in an overflow, so handle the superuser case separately
        try:
            expiration_date = now() + membership_duration
        except OverflowError:
            expiration_date = datetime.max

        member = self.model(
            email=self.normalize_email(email),
            rfid=rfid,
            date_expires=expiration_date,
        )
        member.set_password(password)
        member.save(using=self._db)

        member.move_to_group("Just Joined")

        return member

    def create_superuser(self, email, rfid, password):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        superuser = self.create_member(
            email=email,
            rfid=rfid,
            membership_duration=timedelta.max,
            password=password,
        )

        # Add the rest of the data about the superuser
        superuser.is_admin = True
        superuser.first_name = "Master"
        superuser.last_name = "Admin"
        superuser.phone_number = '+15555555555'
        superuser.certifications.set(Certification.objects.all())
        superuser.save(using=self._db)

        superuser.move_to_group("Admin")

        return superuser


class StafferManager(models.Manager):
    def upgrade_to_staffer(self, member, staff_name, autobiography=None):
        """
        Begins the process of turning a member into a staffer

        :param member: the member to make a staffer
        :param staff_name: the prefix (before @) part of the staffer's staff email
        :param autobiography: the staffers life story
        :return: Staffer
        """
        exc_email = f'{staff_name}@excursionclubucsb.org'
        member.move_to_group("Staff")
        member.date_expires = datetime.max
        member.save()
        if autobiography is not None:
            staffer = self.model(member=member, exc_email=exc_email, autobiography=autobiography)
        else:
            staffer = self.model(member=member, exc_email=exc_email)
        staffer.save()
        return staffer


class Member(AbstractBaseUser, PermissionsMixin):
    """This is the base model for all members (this includes staffers)"""
    objects = MemberManager()

    primary_key = PrimaryKeyField()

    first_name = models.CharField(max_length=50, null=True)
    last_name = models.CharField(max_length=50, null=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    rfid = RFIDField(verbose_name="RFID")
    image = models.ImageField(
        verbose_name="Profile Picture",
        default="shaka.png",
        upload_to=get_profile_pic_upload_location,
        blank=True
    )
    phone_number = PhoneNumberField(unique=False, null=True)

    date_joined = models.DateField(auto_now_add=True)
    date_expires = models.DateField(null=False)

    is_admin = models.BooleanField(default=False)
    group = models.CharField(default="Unset", max_length=30)

    #: This is used by django to determine if users are allowed to login. Leave it, except when banishing someone
    is_active = models.BooleanField(default=True)  # Use is_active_member to check actual activity
    certifications = models.ManyToManyField(Certification, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['date_expires']

    @property
    def is_active_member(self):
        """Return true if the member has a valid membership"""
        return self.has_permission('core.is_active_member')

    @property
    def is_staff(self):
        """
        Property that is used by django to determine whether a user is allowed to log in to the admin: i.e. everyone
        """
        return True

    @property
    def edit_profile_url(self):
        return reverse("admin:core_member_change", kwargs={"object_id": self.pk})

    @property
    def view_profile_url(self):
        return reverse("admin:core_member_detail", kwargs={"pk": self.pk})

    def has_name(self):
        """Check whether the name of this member has been set"""
        return self.first_name and self.last_name

    def get_full_name(self):
        """Return the full name if it is know, or 'New Member' if it is not"""
        if self.has_name():
            return f'{self.first_name} {self.last_name}'
        else:
            return 'New Member'
    get_full_name.short_description = 'Full Name'

    def get_short_name(self):
        # The user is identified by their email address
        return self.first_name

    def get_all_certifications(self):
        all_certs = self.certifications.all()
        return all_certs

    def has_no_certifications(self):
        return len(self.certifications.all()) == 0

    def __str__(self):
        """
        If we know the name of the user, then display their name, otherwise use their email
        """
        if self.has_name():
            return self.get_full_name()
        else:
            return self.email

    def update_admin(self):
        """Updates the admin status of the user in the django system"""
        self.is_admin = self.groups.name == "Admin"

    def expire(self):
        """Expires this member's membership"""
        self.move_to_group("Expired")

    def promote_to_active(self):
        """Move the member to the group of active members"""
        self.move_to_group("Member")

    def extend_membership(self, duration, rfid='', password=''):
        """Add the given amount of time to this member's membership, and optionally update their rfid and password"""

        self.move_to_group("Just Joined")

        if self.date_expires < datetime.date(now()):
            self.date_expires = now() + duration
        else:
            self.date_expires += duration

        if rfid:
            self.rfid = rfid

        if password:
            self.set_password(password)

        return self

    def send_email(self, title, body, from_email, email_host_password):
        """Sends an email to the member"""
        send_mail(title, body, from_email, [self.email],
                  fail_silently=False,
                  auth_user=from_email, auth_password=email_host_password)

    def send_membership_email(self, title, body):
        """Send an email to the member from the membership email"""
        self.send_email(
            title, body,
            settings.MEMBERSHIP_EMAIL_HOST_USER,
            settings.MEMBERSHIP_EMAIL_HOST_PASSWORD
        )

    def send_intro_email(self, finish_signup_url):
        """Send the introduction email with the link to finish signing up to the member"""
        title = "Finish Signing Up"
        # get the absolute path equivalent of going up one level and then into the templates directory
        templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'templates'))
        template_file = open(os.path.join(templates_dir, 'emails', 'intro_email.txt'))
        template = template_file.read()
        body = template.format(finish_signup_url=finish_signup_url)
        self.send_membership_email(title, body)

    def send_expire_soon_email(self):
        """Send an email warning the member that their membership will soon expire"""
        title = "Excursion Club Membership Expiring Soon!"
        templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'templates'))
        template_file = open(os.path.join(templates_dir, 'emails', 'intro_email.txt'))
        template = template_file.read()
        body = template.format(member_name=self.get_full_name(), expiration_date=self.date_expires)
        self.send_membership_email(title, body)

    def has_module_perms(self, app_label):
        """This is required by django, determine whether the user is allowed to view the app"""
        return True

    def has_permission(self, permission_name):
        """Loop through all the permissions of the group associated with this member to see if they have this one"""
        return self.has_perm(permission_name)

    def move_to_group(self, group_name):
        """
        Convenience function to move a member to a group

        Always use this function since it changes the group and the group shortcut field
        """
        new_group = Group.objects.filter(name=group_name)
        self.groups.set(new_group)
        self.group = str(new_group[0])
        self.save()


class Staffer(models.Model):
    """This model provides the staffer profile (all the extra data that needs to be known about staffers)"""
    objects = StafferManager()

    def __str__(self):
        """Gives the staffer a string representation of the staffer name"""
        return self.member.get_full_name()

    member = models.OneToOneField(Member, on_delete=models.CASCADE)
    exc_email = models.EmailField(
        verbose_name='Official ExC Email',
        max_length=255,
        unique=True,
    )
    title = models.CharField(verbose_name="Position Title",
                             default="Excursion Staff!", 
                             max_length=30)
    autobiography = models.TextField(verbose_name="Self Description of the staffer",
                                     default="I am too lazy and lame to upload a bio!")
