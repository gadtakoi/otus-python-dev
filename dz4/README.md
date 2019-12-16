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
ab -n 50000 -c 100 -r http://localhost:8080/
```

```
Server Software:        OTUServer
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        0 bytes

Concurrency Level:      100
Time taken for tests:   4.628 seconds
Complete requests:      50000
Failed requests:        0
Non-2xx responses:      50000
Total transferred:      5050000 bytes
HTML transferred:       0 bytes
Requests per second:    10803.70 [#/sec] (mean)
Time per request:       9.256 [ms] (mean)
Time per request:       0.093 [ms] (mean, across all concurrent requests)
Transfer rate:          1065.60 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    2   1.4      1       9
Processing:     0    8   4.1      7      31
Waiting:        0    6   3.7      5      29
Total:          0    9   4.0      9      33

Percentage of the requests served within a certain time (ms)
  50%      9
  66%     10
  75%     11
  80%     12
  90%     14
  95%     17
  98%     21
  99%     24
 100%     33 (longest request)
```

### Web server test suite:
```git
https://github.com/s-stupnikov/http-test-suite
```
