"""Block write/download endpoints during a local incident."""
from django.http import HttpResponse
from catalog_portal import emergency

class EmergencyStopMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response
    def __call__(self,request):
        blocked_write=request.method not in ("GET","HEAD","OPTIONS") and (
            request.path!="/login/" and request.path!="/logout/"
        )
        blocked_download=(request.path.startswith("/jobs/") and
                          request.path.endswith(("/download/","/report/")))
        if emergency.is_paused() and (blocked_write or blocked_download):
            response=HttpResponse(
                "V3 has paused changes and deliveries pending incident review.",
                status=503,content_type="text/plain; charset=utf-8")
            response["Retry-After"]="300"
            response["Cache-Control"]="no-store"
            return response
        return self.get_response(request)
