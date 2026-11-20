import os
import sys

# Ensure root project directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app


class VercelPathMiddleware:
    """Normalizes WSGI environment for Vercel Serverless Functions.

    When Vercel rewrites requests to /api/index, the original requested URL
    is passed in HTTP_X_MATCHED_PATH or PATH_INFO retains the /api/index prefix.
    This middleware restores the real path so Flask routes (like '/', '/customers',
    '/static/style.css') match cleanly.
    """

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Check headers populated by Vercel's edge router
        matched = (
            environ.get("HTTP_X_MATCHED_PATH")
            or environ.get("HTTP_X_NOW_ROUTE_MATCHES")
            or environ.get("HTTP_X_FORWARDED_URI")
            or environ.get("HTTP_X_ORIGINAL_URL")
            or environ.get("REQUEST_URI")
        )

        if matched:
            environ["PATH_INFO"] = matched.split("?")[0]
        else:
            path_info = environ.get("PATH_INFO", "")
            for prefix in ("/api/index", "/api"):
                if path_info.startswith(prefix):
                    sub = path_info[len(prefix):]
                    environ["PATH_INFO"] = sub if sub else "/"
                    break

        script_name = environ.get("SCRIPT_NAME", "")
        if script_name and environ.get("PATH_INFO", "").startswith(script_name):
            environ["PATH_INFO"] = environ["PATH_INFO"][len(script_name):] or "/"

        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
