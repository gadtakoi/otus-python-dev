import os
import gzip
import sys
import glob
import logging
import collections
from multiprocessing import Pool, cpu_count
from optparse import OptionParser
from queue import Queue, Empty
from threading import Thread
from time import sleep

import appsinstalled_pb2
import memcache

NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])
FINISH = 'finish'
SOCKET_TIMEOUT = 2
DEAD_RETRY = 20
RETRIES = 3
RETRIES_SLEEP = 1
GET_TIMEOUT = 0.1
CHUNK_SIZE = 10


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def insert_appsinstalled(memc, chunks: dict, dry_run=False):
    processed = errors = 0
    try:
        if dry_run:
            for key, value in chunks.items():
                logging.debug('%s - %s -> %s' % (memc, key, value))
                processed += 1
        else:
            processed, errors = memcache_set(memc, chunks)
    except Exception as e:
        logging.exception("Cannot write to memc %s: %s" % (memc, e))
    return processed, errors


def memcache_set(memc, chunks):
    notset_keys = memc.set_multi(chunks)
    retries = 0
    while notset_keys and retries < RETRIES:
        notset_keys = memc.set_multi({
            key: chunks[key]
            for key in notset_keys
        })
        retries += 1
        sleep(RETRIES_SLEEP)
    errors = len(notset_keys)
    return len(chunks.keys()) - errors, errors


def prepare_appsinstalled(appsinstalled):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = '%s:%s' % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    return (key, packed)


def parse_appsinstalled(line):
    line = str(line)
    line_parts = line.strip().split("\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


class Worker(Thread):
    def __init__(self, job_pool, memc, results_queue, dry_run=False):
        super().__init__()
        self.job_pool = job_pool
        self.results_queue = results_queue
        self.memc = memc
        self.dry_run = dry_run

    def run(self) -> None:
        logging.info('[Worker %s] Start thread: %s' % (os.getpid(), self.name))
        processed = 0
        errors = 0
        chunk = dict()
        while True:
            try:
                try:
                    line = self.job_pool.get(timeout=GET_TIMEOUT)
                except Empty:
                    continue

                chunk[line[0]] = line[1]

                if line == FINISH:
                    self.results_queue.put((processed, errors))
                    self.job_pool.task_done()
                    logging.info('[Worker %s] Stop thread: %s' % (os.getpid(), self.name))
                    break
                else:
                    if len(chunk) == CHUNK_SIZE:
                        proc_items, err_items = insert_appsinstalled(self.memc, chunk)
                        processed += proc_items
                        errors += err_items
                        chunk = dict()
                        self.job_pool.task_done()
            except Empty:
                continue


def file_handler(fn, options, device_memc):
    jobs_pool = {}
    treads_pool = list()
    results_queue = Queue()
    for dev_type, address in device_memc.items():
        memc = memcache.Client(servers=[address], socket_timeout=SOCKET_TIMEOUT, dead_retry=DEAD_RETRY)
        jobs_pool[dev_type] = Queue()
        thread = Worker(jobs_pool[dev_type], memc, results_queue, options.dry)
        treads_pool.append(thread)
        thread.start()

    processed = errors = 0
    logging.info('[Worker %s] Processing %s' % (os.getpid(), fn))
    count = 0
    fd = gzip.open(fn)
    for line in fd:
        line = line.decode().strip()
        if not line:
            continue
        appsinstalled = parse_appsinstalled(line)
        jobs_pool[appsinstalled.dev_type].put(prepare_appsinstalled(appsinstalled))

        count = count + 1
        if count % 300000 == 0:
            while True:
                size = jobs_pool[appsinstalled.dev_type].qsize()
                if size < 1000:
                    break
                sleep(0.05)

    for d_type in device_memc:
        jobs_pool[d_type].put(FINISH)

    for tp in treads_pool:
        tp.join()

    while not results_queue.empty():
        result = results_queue.get(timeout=0.1)
        processed += result[0]
        errors += result[1]

    if not processed:
        fd.close()
        return fn

    err_rate = float(errors) / processed
    if err_rate < NORMAL_ERR_RATE:
        logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
    else:
        logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
    fd.close()

    return fn


def main(options):
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    pool = Pool(options.workers)

    process_args = ((fn, options, device_memc) for fn in sorted(glob.iglob(options.pattern)))
    for file_name in pool.starmap(file_handler, process_args):
        dot_rename(file_name)


def prototest():
    sample = "idfa\t1rfw452y52g2gg4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default="/data/appsinstalled/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    op.add_option('-w', '--workers', action='store', type=int, default=cpu_count() + 1)

    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
