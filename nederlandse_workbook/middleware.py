class SecurityHeadersMiddleware:
    """Sets Content-Security-Policy and related security headers on responses.

    Applied only in production (added to MIDDLEWARE in production_settings.py).
    'unsafe-inline'/'unsafe-eval' are required by the mobile-menu and graph
    inline scripts plus Alpine.js expression evaluation; external script/style
    hosts are the pinned CDNs used in the templates.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
            "img-src 'self' data:; "
            "font-src 'self' data: https://cdnjs.cloudflare.com; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
