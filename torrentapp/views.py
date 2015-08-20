from django.shortcuts import render, redirect
from django.http import HttpResponseNotFound, HttpResponse
from django.contrib.auth.decorators import login_required
from . import models
from . import settings
from binascii import hexlify

def index(request):
    if request.user.is_authenticated():
        profile = models.Profile.get(request.user)

        torrent = models.Torrent.get(request.user, 'lorem.txt')

        tracker_url = profile.get_tracker_url()
        return render(request, 'index.html', {
            'tracker_url': tracker_url,
            'info_hash': hexlify(torrent.info_hash)[:8]})
    else:
        return render(request, 'index.html')

def redirect_to_front(request):
    return redirect('/')

@login_required
def log(request):
    return render(request, 'log.html', {
        'logs': models.LogEntry.objects.filter(user=request.user).order_by('-timestamp')[:100]
    })

@login_required
def torrent(request, name):
    if name not in ['lorem.txt']:
        return HttpResponseNotFound()
    torrent_obj = models.Torrent.get(request.user, name)
    return HttpResponse(torrent_obj.encode(), content_type='application/octet-stream')

def push_log(request):
    info_hash = request.REQUEST['info_hash']
    msg = request.REQUEST['msg']
    torrent = models.Torrent.objects.get(info_hash=info_hash)
    models.LogEntry.log(user=torrent.user, module='client', text=msg)
    return HttpResponse('ok')

def torrent_data(request):
    info_hash = request.REQUEST['info_hash']
    try:
        torrent = models.Torrent.objects.get(info_hash=info_hash)
    except models.Torrent.DoesNotExist:
        return HttpResponseNotFound()
    else:
        return HttpResponse(torrent.get_data(), content_type='application/octet-stream')
