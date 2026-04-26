# COMP2322 Multi-thread Web Server

**Course Project**

---

## 1. Requirements

- Python 3.6 or higher
- No additional libraries required (uses only Python standard library)

---

## 2. How to Run

### 2.1 Start the Server
Open a terminal in the project directory and run:
```bash
python webserver.py 8080
```

Expected output when server starts:
```text
Server started on port 8080
Serving files from: test_files
Log file: server.log
Press Ctrl+C to stop
```

### 2.2 Stop the Server
Press Ctrl + C in the terminal.

---

## 3. How to Test

### 3.1 Test GET Text File (200 OK)
Open a new terminal(terminal2) and run:
```bash
curl http://127.0.0.1:8080/index.html
```
Expected output:
```text
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<h1>Hello from Web Server!</h1>
<p>This is a test page.</p>
</body>
</html>
```
### 3.2 Test GET Image File (200 OK)
Place a PNG image named test.png in the test_files/ folder, then run:
```bash
curl -o downloaded.png http://127.0.0.1:8080/test.png
```
Expected output: 
```text
% Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 10346  100 10346    0     0  4472k      0 --:--:-- --:--:-- --:--:-- 5051k
```
The image downloads successfully to downloaded.png.

### 3.3 Test HEAD Command (200 OK)
```bash
curl -I http://127.0.0.1:8080/test.txt
```
Expected output: 
```text
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 45
Last-Modified: Sat, 25 Apr 2026 06:26:00 GMT
Connection: keep-alive
```

### 3.4 Test 400 Bad Request
```bash
printf "asdf\r\n\r\n" | nc 127.0.0.1 8080
```
Expected output: 
```text
HTTP/1.1 400 Bad Request
Content-Type: text/html
Content-Length: 107
Connection: close

<html><body><h1>400 Bad Request</h1><p>The request could not be understood by the server.</p></body></html>% 
```

### 3.5 Test 403 Forbidden3
```bash
printf "GET /../../webserver.py HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n" | nc 127.0.0.1 8080
```
Expected output: 
```text
HTTP/1.1 403 Forbidden
Content-Type: text/html
Content-Length: 105
Connection: close

<html><body><h1>403 Forbidden</h1><p>You don't have permission to access this resource.</p></body></html>%   
```

### 3.6 Test 404 Not Found
```bash
curl http://127.0.0.1:8080/notexist.html
```
Expected output: 
```text
<html><body><h1>404 Not Found</h1><p>The requested file 'notexist.html' was not found on this server.</p></body></html>%  
```

### 3.7 Test 304 Not Modified (GET)
```bash
curl -I http://127.0.0.1:8080/index.html 2>/dev/null | grep -i last-modified
```
```bash
curl -v -H "If-Modified-Since: Sat, 25 Apr 2026 06:25:37 GMT" http://127.0.0.1:8080/index.html
```
Expected output: 
```text
Last-Modified: Sat, 25 Apr 2026 06:25:37 GMT
```
```text
*   Trying 127.0.0.1:8080...
* Connected to 127.0.0.1 (127.0.0.1) port 8080
* using HTTP/1.x
> GET /index.html HTTP/1.1
> Host: 127.0.0.1:8080
> User-Agent: curl/8.12.1
> Accept: */*
> If-Modified-Since: Sat, 25 Apr 2026 06:25:37 GMT
> 
* Request completely sent off
< HTTP/1.1 304 Not Modified
< Last-Modified: Sat, 25 Apr 2026 06:25:37 GMT
< Connection: keep-alive
< 
* Connection #0 to host 127.0.0.1 left intact
```
### 3.8 Test 304 Not Modified (HEAD)
```bash
curl -I http://127.0.0.1:8080/index.html 2>/dev/null | grep -i last-modified
```
```bash
curl -I -H "If-Modified-Since: Sat, 25 Apr 2026 06:25:37 GMT" http://127.0.0.1:8080/index.html
```
Expected output: 
```text
Last-Modified: Sat, 25 Apr 2026 06:25:37 GMT
```
```text
HTTP/1.1 304 Not Modified
Last-Modified: Sat, 25 Apr 2026 06:25:37 GMT
Connection: keep-alive
```
### 3.9 Test Connection: close
```bash
curl -H "Connection: close" http://127.0.0.1:8080/index.html -v 2>&1 | grep -i connection
```
Expected output: 
```text
> Connection: close
< Connection: close
* shutting down connection #0
```

### 3.10 Test Connection: keep-alive
```bash
curl -v http://127.0.0.1:8080/index.html 2>&1 | grep -i connection
```
Expected output: 
```text
< Connection: keep-alive
* Connection #0 to host 127.0.0.1 left intact
```

### 3.11 Test Multi-threading
```bash
for i in {1..5}; do curl -s http://127.0.0.1:8080/index.html > /dev/null & done; wait
```
Expected output: 
```text
[2] xxxx (five times)
[x]    done    curl -s http://127.0.0.1:8080/index.html > /dev/null (five times)
```

### 3.12Test Multi-threading with Connection: close
```bash
for i in {1..5}; do 
    curl -H "Connection: close" -s http://127.0.0.1:8080/index.html > /dev/null &
done; wait
```
Expected output: 
```text
[2] xxxx (five times)
[x]  + done       curl -H "Connection: close" -s http://127.0.0.1:8080/index.html > /dev/null (five times)
```

### 3.13 Test with Browser
Open a web browser and enter:
```text
http://127.0.0.1:8080/index.html
```
Expected result: The browser displays "Hello from Web Server!" with proper HTML formatting.
Terminal1(not terminal2) Expected output:
```text
Connection] Accepted connection from ('127.0.0.1', 61796)
[304 Not Modified] 127.0.0.1 - index.html
or
Connection] Accepted connection from ('127.0.0.1', 61796)
[200 OK] 127.0.0.1 - index.html
```

---

## 4. Log File

All requests are logged to server.log in the project directory. Each log entry contains:
- Timestamp 
- Client IP address
- Requested file name
- HTTP status code

Example log content:
```text
2026-04-25 22:09:47 | 127.0.0.1 | test.txt | 200
2026-04-25 22:09:54 | 127.0.0.1 | asdf | 400
2026-04-25 22:10:01 | 127.0.0.1 | /../../webserver.py | 403
2026-04-25 22:10:09 | 127.0.0.1 | notexist.html | 404
2026-04-25 22:10:20 | 127.0.0.1 | index.html | 200
2026-04-25 22:10:53 | 127.0.0.1 | index.html | 304
```
