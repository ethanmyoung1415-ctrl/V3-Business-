"""Block non-loopback access to the synthetic-only V3 portal."""
import ipaddress
from django.conf import settings
from django.http import HttpResponseForbidden

class LocalOnlyPortal:
    def __init__(self,get_response):
        self.get_response=get_response
    def __call__(self,request):
        # Never trust X-Forwarded-For for authorizing local development.
        # Reverse proxies are explicitly out of scope for this demo.
        try:
            remote=ipaddress.ip_address(request.META.get("REMOTE_ADDR",""))
        except ValueError:
            remote=None
        if remote is None or not remote.is_loopback:
            return HttpResponseForbidden("This portal is restricted to local development.")
        return self.get_response(request)
