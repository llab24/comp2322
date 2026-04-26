"""
COMP2322Project - Multi-thread Web Server
24127442d
"""

import socket
import threading
import os
import time
import datetime
import email.utils
import mimetypes

# Configuration
SERVER_HOST = '127.0.0.1'  # Listen on localhost only
SERVER_PORT = 8080  # Default port (can be changed via command line)
WEB_ROOT = 'test_files'  # Directory containing web files
LOG_FILE = 'server.log'


class WebServer:
    def __init__(self, port=SERVER_PORT):
        self.port = port
        self.server_socket = None
        self.running = True
        
    def start(self):
        """Start the web server"""
        try:
            # Create TCP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow reuse of address (helps with quick restarts)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to address and port
            self.server_socket.bind((SERVER_HOST, self.port))
            # Start listening (max 5 pending connections)
            self.server_socket.listen(5)
            
            print(f"Server started on port {self.port}")
            print(f"Serving files from: {WEB_ROOT}")
            print(f"Log file: {LOG_FILE}")
            print("Press Ctrl+C to stop\n")
            
            # Main loop - accept incoming connections
            while self.running:
                try:
                    client_socket, client_addr = self.server_socket.accept()
                    print(f"[Connection] Accepted connection from {client_addr}")
                    
                    # Create a new thread to handle this client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except OSError:
                    if self.running:
                        raise
                    break
                    
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")
    
    def handle_client(self, client_socket, client_addr):
        """Handle a single client connection (runs in its own thread)"""
        try:
            # Set timeout for receiving data
            client_socket.settimeout(5)
            
            # Receive the HTTP request
            request_data = b''
            while True:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    request_data += chunk
                    # Check if we've received the complete headers (double CRLF)
                    if b'\r\n\r\n' in request_data:
                        break
                except socket.timeout:
                    break
            
            if not request_data:
                client_socket.close()
                return
            
            # Decode and parse the request
            request_str = request_data.decode('utf-8', errors='replace')
            request_lines = request_str.split('\r\n')
            
            if not request_lines:
                self.send_error_response(client_socket, 400, client_addr, "")
                client_socket.close()
                return
            
            # Parse the request line
            request_line = request_lines[0]
            parts = request_line.split(' ')
            
            #check for malformed request
            if len(parts) < 2 or parts[0] not in ['GET', 'HEAD']:
                self.send_error_response(client_socket, 400, client_addr, request_line)
                client_socket.close()
                return
            
            method = parts[0].upper()
            path = parts[1]
            http_version = parts[2] if len(parts) > 2 else 'HTTP/1.1'
            
            # Parse headers
            headers = {}
            connection_close = False
            
            for line in request_lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            if 'connection' in headers:
                if headers['connection'].lower() == 'close':
                    connection_close = True
            else:
                # HTTP 1.0 defaults to close, HTTP 1.1 defaults to keep-alive
                if http_version == 'HTTP/1.0':
                    connection_close = True
            
            # Process the request - pass connection_close flag
            self.process_request(client_socket, method, path, http_version, headers, client_addr, connection_close)
            
            # Close connection if needed
            if connection_close:
                client_socket.close()
                
        except Exception as e:
            print(f"Error handling client {client_addr}: {e}")
            try:
                client_socket.close()
            except:
                pass
    
    def process_request(self, client_socket, method, path, http_version, headers, client_addr, connection_close):
        """Process the HTTP request and send response"""

        if '..' in path or path.startswith('/.') or '\\' in path:
            self.send_error_response(client_socket, 403, client_addr, path, connection_close)
            client_socket.close()
            return
        
        # Remove query parameters (anything after '?')
        file_path = path.split('?')[0]
        
        # Default to index.html if path is root
        if file_path == '/' or file_path == '':
            file_path = '/index.html'
        
        # Convert to file system path
        if file_path.startswith('/'):
            file_path = file_path[1:]
        
        full_path = os.path.join(WEB_ROOT, file_path)
        
        # Security: ensure the path is within WEB_ROOT
        try:
            real_full_path = os.path.realpath(full_path)
            real_web_root = os.path.realpath(WEB_ROOT)
            if not real_full_path.startswith(real_web_root):
                self.send_error_response(client_socket, 403, client_addr, file_path, connection_close)
                return
        except:
            self.send_error_response(client_socket, 403, client_addr, file_path, connection_close)
            return
        
        # Check if file exists
        if not os.path.exists(full_path):
            self.send_error_response(client_socket, 404, client_addr, file_path, connection_close)
            return
        
        # Check if it's a file (not a directory)
        if os.path.isdir(full_path):
            # Try to serve index.html from directory
            index_path = os.path.join(full_path, 'index.html')
            if os.path.exists(index_path) and os.path.isfile(index_path):
                full_path = index_path
            else:
                self.send_error_response(client_socket, 404, client_addr, file_path, connection_close)
                return
        
        # Get file statistics
        file_stat = os.stat(full_path)
        last_modified = file_stat.st_mtime
        file_size = file_stat.st_size
        last_modified_str = email.utils.formatdate(last_modified, usegmt=True)
        
        
        # Handle If-Modified-Since for 304 Not Modified
        if 'if-modified-since' in headers:
            try:
                if_modified_since = email.utils.parsedate_to_datetime(headers['if-modified-since'])
                
                # Convert file last_modified to aware datetime (UTC) for correct comparison
                last_modified_dt = datetime.datetime.fromtimestamp(last_modified, tz=datetime.timezone.utc)
                
                last_modified_dt = last_modified_dt.replace(microsecond=0)

                # If file has NOT been modified since the If-Modified-Since time → return 304
                if last_modified_dt <= if_modified_since:
                    self.send_not_modified_response(client_socket, last_modified_str, client_addr, file_path, connection_close)
                    return
            except (ValueError, TypeError, OverflowError):
                # Invalid date format, ignore the header (per HTTP spec)
                pass
    
        # Determine content type
        content_type = self.get_content_type(full_path)
        
        # Handle HEAD method
        if method == 'HEAD':
            self.send_head_response(client_socket, content_type, file_size, last_modified_str, client_addr, file_path, connection_close)
            return
        
        # Handle GET method
        if method == 'GET':
            self.send_get_response(client_socket, full_path, content_type, file_size, last_modified_str, client_addr, file_path, connection_close)
            return
        
        # Method not allowed
        self.send_error_response(client_socket, 400, client_addr, f"Unsupported method: {method}", connection_close)
    
    def send_get_response(self, client_socket, file_path, content_type, file_size, last_modified_str, client_addr, requested_file, connection_close):
        """Send a complete HTTP response with file content"""
        try:
            # Read the file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            connection_header = "close" if connection_close else "keep-alive"
            
            # Build response headers
            response_line = "HTTP/1.1 200 OK\r\n"
            headers = (
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {file_size}\r\n"
                f"Last-Modified: {last_modified_str}\r\n"
                f"Connection: {connection_header}\r\n"
                f"\r\n"
            )
            
            # Send headers and content
            client_socket.send(response_line.encode())
            client_socket.send(headers.encode())
            client_socket.send(file_content)
            
            # Log the request
            self.log_request(client_addr, requested_file, 200)
            print(f"[200 OK] {client_addr[0]} - {requested_file}")
            
        except Exception as e:
            print(f"Error sending file {file_path}: {e}")
            self.send_error_response(client_socket, 404, client_addr, requested_file, connection_close)
    
    def send_head_response(self, client_socket, content_type, file_size, last_modified_str, client_addr, requested_file, connection_close):
        """Send only headers (no content) for HEAD request"""
        
        connection_header = "close" if connection_close else "keep-alive"
        
        response_line = "HTTP/1.1 200 OK\r\n"
        headers = (
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {file_size}\r\n"
            f"Last-Modified: {last_modified_str}\r\n"
            f"Connection: {connection_header}\r\n"
            f"\r\n"
        )
        
        client_socket.send(response_line.encode())
        client_socket.send(headers.encode())
        
        # Log the request
        self.log_request(client_addr, requested_file, 200)
        print(f"[200 OK (HEAD)] {client_addr[0]} - {requested_file}")
    
    def send_not_modified_response(self, client_socket, last_modified_str, client_addr, requested_file, connection_close):
        """Send 304 Not Modified response"""
        
        connection_header = "close" if connection_close else "keep-alive"
        
        response_line = "HTTP/1.1 304 Not Modified\r\n"
        headers = (
            f"Last-Modified: {last_modified_str}\r\n"
            f"Connection: {connection_header}\r\n"
            f"\r\n"
        )
        
        client_socket.send(response_line.encode())
        client_socket.send(headers.encode())
        
        # Log the request
        self.log_request(client_addr, requested_file, 304)
        print(f"[304 Not Modified] {client_addr[0]} - {requested_file}")
    
    def send_error_response(self, client_socket, status_code, client_addr, requested_file, connection_close=True):
        """Send appropriate error response based on status code"""
        
        if status_code == 400:
            status_text = "Bad Request"
            body = "<html><body><h1>400 Bad Request</h1><p>The request could not be understood by the server.</p></body></html>"
        elif status_code == 403:
            status_text = "Forbidden"
            body = "<html><body><h1>403 Forbidden</h1><p>You don't have permission to access this resource.</p></body></html>"
        elif status_code == 404:
            status_text = "Not Found"
            body = f"<html><body><h1>404 Not Found</h1><p>The requested file '{requested_file}' was not found on this server.</p></body></html>"
        else:
            status_code = 500
            status_text = "Internal Server Error"
            body = "<html><body><h1>500 Internal Server Error</h1></body></html>"
        
        #Error responses should always close connection
        response_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
        headers = (
            f"Content-Type: text/html\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        
        client_socket.send(response_line.encode())
        client_socket.send(headers.encode())
        client_socket.send(body.encode())
        
        # Log the request
        self.log_request(client_addr, requested_file, status_code)
        print(f"[{status_code} {status_text}] {client_addr[0]} - {requested_file}")
    
    def get_content_type(self, file_path):
        """Determine MIME type based on file extension"""
        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None:
            return 'text/plain'
        return content_type
    
    def log_request(self, client_addr, requested_file, status_code):
        """Write request information to log file"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        client_host = client_addr[0]
        log_entry = f"{timestamp} | {client_host} | {requested_file} | {status_code}\n"
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to log file: {e}")


def main():
    """Main entry point"""
    import sys
    
    # Get port from command line if provided
    port = SERVER_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            print(f"Usage: python webserver.py [port]")
            sys.exit(1)
    
    # Make sure web root directory exists
    if not os.path.exists(WEB_ROOT):
        os.makedirs(WEB_ROOT)
        print(f"Created directory: {WEB_ROOT}")
        print(f"Please add test files to {WEB_ROOT}/")
    
    # Start the server
    server = WebServer(port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == "__main__":
    main()