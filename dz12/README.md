### Requirements
memcached

```shell script
memcached -l 0.0.0.0:33013,0.0.0.0:33014,0.0.0.0:33015,0.0.0.0:33016
```
or
```shell script
docker-compose up
```

### Run
time go run memc_load_multi.go -pattern=data/*.tsv.gz




