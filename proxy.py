#!/usr/bin/env python3
"""
Reverse proxy for path-based routing with referer-aware fallback.
Routes /green/* -> localhost:8010 and /white/* -> localhost:8011
Also handles requests without prefix by checking the Referer header.
"""

import http.server
import urllib.request
import urllib.error

GREEN_PORT = 8010
WHITE_PORT = 8011
PROXY_PORT = 8080


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def get_target_from_referer(self):
        """Check Referer header to determine which agent to route to."""
        referer = self.headers.get('Referer', '')
        if '/green' in referer:
            return GREEN_PORT
        elif '/white' in referer:
            return WHITE_PORT
        return None

    def do_request(self):
        path = self.path
        target_path = path
        target_port = None
        
        # Route based on path prefix
        if path.startswith('/green'):
            target_port = GREEN_PORT
            target_path = path[6:] if len(path) > 6 else '/'
        elif path.startswith('/white'):
            target_port = WHITE_PORT
            target_path = path[6:] if len(path) > 6 else '/'
        else:
            # No prefix - check Referer header
            target_port = self.get_target_from_referer()
            if target_port is None:
                self.send_error(404, f"Unknown path: {path}. Use /green/... or /white/...")
                return
            # Keep the original path (the controller expects /status, /agents, etc.)
            target_path = path

        target_url = f"http://localhost:{target_port}{target_path}"
        
        try:
            # Read request body if present
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Forward the request
            req = urllib.request.Request(
                target_url,
                data=body,
                method=self.command
            )
            
            # Copy headers (except Host)
            for key, value in self.headers.items():
                if key.lower() not in ('host', 'content-length'):
                    req.add_header(key, value)
            
            # Make the request
            with urllib.request.urlopen(req, timeout=300) as response:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in ('transfer-encoding',):
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
                
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for key, value in e.headers.items():
                if key.lower() not in ('transfer-encoding',):
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(e.read())
        except urllib.error.URLError as e:
            self.send_error(502, f"Cannot reach {target_url}: {e.reason}")
        except Exception as e:
            self.send_error(500, str(e))

    def do_GET(self):
        self.do_request()
    
    def do_POST(self):
        self.do_request()
    
    def do_PUT(self):
        self.do_request()
    
    def do_DELETE(self):
        self.do_request()
    
    def do_PATCH(self):
        self.do_request()
    
    def do_OPTIONS(self):
        self.do_request()

    def log_message(self, format, *args):
        print(f"[Proxy] {self.address_string()} - {format % args}")


if __name__ == '__main__':
    print(f"Starting proxy on port {PROXY_PORT}")
    print(f"  /green/* -> localhost:{GREEN_PORT}")
    print(f"  /white/* -> localhost:{WHITE_PORT}")
    print(f"  (Also routes based on Referer header)")
    print()
    server = http.server.HTTPServer(('', PROXY_PORT), ProxyHandler)
    server.serve_forever()
