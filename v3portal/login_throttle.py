"""Local-development login throttling; NOT distributed production rate limiting."""
import hashlib
import ipaddress
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.encoding import force_str

WINDOW_SECONDS=900
MAX_ATTEMPTS=8

class LocalLoginThrottle:
    def __init__(self,get_response):
        self.get_response=get_response
    def __call__(self,request):
        if request.path!="/login/" or request.method!="POST":
            return self.get_response(request)
        address=request.META.get("REMOTE_ADDR","")
        try:
            ip=ipaddress.ip_address(address).compressed
        except ValueError:
            return HttpResponse("Invalid connection.",status=403)
        username=force_str(request.POST.get("username","")).casefold().strip()[:80]
        # Hash rather than persist submitted usernames in the cache key.
        fingerprint=hashlib.sha256((ip+"|"+username).encode("utf-8")).hexdigest()
        key="v3_local_login_attempts:"+fingerprint
        count=cache.get(key,0)
        if count>=MAX_ATTEMPTS:
            response=HttpResponse("Too many login attempts. Try again later.",status=429)
            response["Retry-After"]=str(WINDOW_SECONDS)
            return response
        # Local single-process throttle; production needs a distributed,
        # independently reviewed service and stronger identity controls.
        cache.set(key,count+1,timeout=WINDOW_SECONDS)
        return self.get_response(request)
