"""Simple health check HTTP server for Azure Container Apps"""

import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import json

class HealthStatus:
    def __init__(self):
        self.last_scrape = None
        self.scrape_count = 0
        self.start_time = datetime.now()
        self.status = "starting"
        self.errors = []

    def update_scrape(self, success=True, error=None):
        self.last_scrape = datetime.now()
        self.scrape_count += 1
        self.status = "healthy" if success else "unhealthy"
        
        if error:
            self.errors.append({
                "timestamp": self.last_scrape.isoformat(),
                "error": str(error)
            })
            # Keep only last 10 errors
            self.errors = self.errors[-10:]

health_status = HealthStatus()

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Calculate uptime
            uptime_seconds = (datetime.now() - health_status.start_time).total_seconds()
            
            # Time since last scrape
            time_since_scrape = None
            if health_status.last_scrape:
                time_since_scrape = (datetime.now() - health_status.last_scrape).total_seconds()
            
            response = {
                "status": health_status.status,
                "uptime_seconds": uptime_seconds,
                "scrape_count": health_status.scrape_count,
                "last_scrape": health_status.last_scrape.isoformat() if health_status.last_scrape else None,
                "time_since_last_scrape_seconds": time_since_scrape,
                "recent_errors": health_status.errors[-3:] if health_status.errors else []
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'HardRock Multi-League Scraper - OK')
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP server logging
        pass

def start_health_server(port=8080):
    """Start health check server in background thread"""
    server = HTTPServer(('', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, health_status