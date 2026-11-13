"""Defensive response headers for preproduction V3 portal pages."""
class PrivatePortalHeaders:
    def __init__(self,get_response):
        self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        if request.path.startswith("/static/"):
            return response
        response["Cache-Control"]="no-store, private"
        response["Referrer-Policy"]="no-referrer"
        response["X-Content-Type-Options"]="nosniff"
        response["Content-Security-Policy"]=(
            "default-src 'none'; style-src 'unsafe-inline'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        response["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
        return response
