from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _
from config.settings import MEDIA_URL


class User(AbstractUser):
    email = models.EmailField(_('email address'), blank=False, unique=True)
    avatar = models.ImageField(upload_to='images/avatars', blank=True, null=True)
    fio = models.CharField(verbose_name='ФИО', max_length=255, null=True, blank=True)
    is_staff = models.BooleanField(default=False)

    def avatar_view(self):
        if self.avatar:
            return '{}{}'.format(MEDIA_URL, escape(self.avatar))

    def get_full_name(self):
        if self.fio:
            full_name = self.fio
        elif self.first_name or self.last_name:
            full_name = '{} {}'.format(self.first_name, self.last_name)
        else:
            full_name = self.username
        return full_name.strip()
