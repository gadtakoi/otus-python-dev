# Asyncronous HTTP server, with asyncio library

### Start server:
```shell script 
python3 httpd.py
``` 

### Start options:
- **-p** - server port (default: 80)
- **-w** - workers (default: 64, but no more than your processor cores)
- **-r** - DOCUMENT_ROOT (default: current folder)
- **-l** - output log file

### Test server specs:
Core i5-3470 CPU @ 3.20GHz, 4 cores, 16RAM, SSD

### Load test results:
```shell script
ab -n 50000 -c 100 -r http://127.0.0.1:80/httptest/dir2/
```

```
Server Software:        OTUServer
Server Hostname:        localhost
Server Port:            80

Document Path:          /httptest/dir2/
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   7.477 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      8650000 bytes
HTML transferred:       1700000 bytes
Requests per second:    6687.18 [#/sec] (mean)
Time per request:       14.954 [ms] (mean)
Time per request:       0.150 [ms] (mean, across all concurrent requests)
Transfer rate:          1129.77 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1   0.9      1       7
Processing:     1   14   6.4     13      57
Waiting:        0   12   5.8     11      56
Total:          1   15   6.5     14      59

Percentage of the requests served within a certain time (ms)
  50%     14
  66%     16
  75%     18
  80%     19
  90%     23
  95%     26
  98%     31
  99%     33
 100%     59 (longest request)
```

### Web server test suite:
```git
https://github.com/s-stupnikov/http-test-suite
```

### Check ../

```bash
telnet 127.0.0.1 80
```
```
GET /httptest/dir2/../../../../zzz.html HTTP/1.1
```

### Check length in HEAD 
```bash
curl -I http://127.0.0.1/httptest/dir2/
```