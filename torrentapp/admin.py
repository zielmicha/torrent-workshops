from django.contrib import admin
from . import models

class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp', 'module', 'text')

admin.site.register(models.LogEntry, LogEntryAdmin)

class TorrentAdmin(admin.ModelAdmin):
    list_display = ('user', 'info_hash', 'name', 'token')

admin.site.register(models.Torrent, TorrentAdmin)
