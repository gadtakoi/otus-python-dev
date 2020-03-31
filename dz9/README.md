### Requirements
Python 3.8
requirements.txt
memcached

```shell script
memcached -l 0.0.0.0:33013,0.0.0.0:33014,0.0.0.0:33015,0.0.0.0:33016
```
or
```shell script
docker-compose up
```

### Run
python memc_load.py --pattern=data/*.tsv.gz



