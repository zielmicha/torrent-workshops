from django.db import models
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings

import os
import base64
import binascii

import torrent

def gen_tracker():
    return base64.b32encode(os.urandom(8)).decode('utf8').strip('=')

class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    tracker_token = models.CharField(max_length=60, default=gen_tracker)

    @classmethod
    def get(cls, user):
        profile, q = cls.objects.get_or_create(user=user)
        return profile

    def get_tracker_url(self, part):
        return settings.SITE_URL + 'tracker/' + self.tracker_token + '_' + part + '/announce'

class LogEntry(models.Model):
    user = models.ForeignKey(User, related_name='+')
    timestamp = models.DateTimeField(auto_now_add=True)
    module = models.CharField(max_length=50)
    text = models.TextField(max_length=2000)

    @classmethod
    def log(cls, user, module, text):
        LogEntry(user=user, module=module, text=text).save()

class Torrent(models.Model):
    user = models.ForeignKey(User, related_name='+')
    info_hash = models.CharField(max_length=60)
    name = models.CharField(max_length=60)
    token = models.CharField(max_length=60)

    def get_data(self):
        if self.name.endswith('.txt'):
            data = open('torrentapp/templates/%s' % self.name, 'rb').read()
            return data.replace(b'{{ token }}', self.token.encode('utf8'))
        else:
            data = open('%s' % self.name, 'rb').read()
            return data + self.token.encode()

    @classmethod
    @transaction.atomic
    def get(cls, user, name, part):
        assert name in ['lorem.txt', 'Xbox-4.avi']
        assert '/' not in name

        if name.endswith('.txt'):
            piece_length = 4096
        else:
            piece_length = 64 * 1024

        try:
            torrent_model = Torrent.objects.get(user=user, name=name)
        except Torrent.DoesNotExist:
            rand = base64.b32encode(os.urandom(16)).decode('utf8').strip('=')
            torrent_model = Torrent(user=user, name=name, token=rand)

        torrent_obj = torrent.Torrent.make_from_data(
            torrent_model.get_data(),
            piece_length=piece_length,
            comment=('Torrent %s for user %s.' % (name, user.username)).encode('utf8'),
            announce=user.profile.get_tracker_url(part).encode(),
            name=name.encode('utf8'))

        if not torrent_model.pk:
            torrent_model.info_hash = binascii.hexlify(torrent_obj.info_hash)
            LogEntry.log(user, 'make torrent',
                         'Torrent for %s created with info_hash %s.' % (
                             name, torrent_model.info_hash.decode('utf8')))
            torrent_model.save()

        # assert binascii.hexlify(torrent_obj.info_hash) == torrent_model.info_hash, \
        #     (binascii.hexlify(torrent_obj.info_hash), torrent_model.info_hash)

        return torrent_obj
