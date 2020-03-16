import os
import sys
import time
import glob
import gzip
import logging
import memcache
import collections

from threading import Thread
from queue import Queue, Empty
from optparse import OptionParser
from multiprocessing import Pool, cpu_count

import appsinstalled_pb2

NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple('AppsInstalled', ['dev_type', 'dev_id', 'lat', 'lon', 'apps'])
SENTINEL = object()
CHUNK_SIZE = 50


class MemcacheWriter(Thread):
    def __init__(self, job_queue, result_queue, memc, dry_run=False, attempts=1):
        super().__init__()
        self.job_queue = job_queue
        self.result_queue = result_queue
        self.memc = memc
        self.dry_run = dry_run
        self.attempts = attempts
        self.daemon = True

    def run(self):
        logging.info('[Worker %s] Start thread: %s' % (os.getpid(), self.name))
        processed = errors = 0
        while True:
            try:
                chunks = self.job_queue.get(timeout=0.1)
                if chunks == SENTINEL:
                    self.result_queue.put((processed, errors))
                    logging.info('[Worker %s] Stop thread: %s' % (os.getpid(), self.name))
                    break
                else:
                    proc_items, err_items = self.insert_appsinstalled(chunks)
                    processed += proc_items
                    errors += err_items
            except Empty:
                continue

    def insert_appsinstalled(self, chunks):
        processed = errors = 0
        try:
            if self.dry_run:
                for key, value in chunks.items():
                    logging.debug('%s - %s -> %s' % (self.memc, key, value))
                    processed += 1
            else:
                processed, errors = self.memcache_set(self.memc, chunks)
        except Exception as e:
            logging.exception('Cannot write to memc %s: %s' % (self.memc.servers[0], e))
        return processed, errors

    def memcache_set(self, memc, chunks):
        failed_keys = memc.set_multi(chunks)
        attempts = 0
        while failed_keys and attempts < self.attempts:
            failed_keys = memc.set_multi({
                key: chunks[key]
                for key in failed_keys
            })
            attempts += 1
            time.sleep(1)
        errors = len(failed_keys)
        return len(chunks.keys()) - errors, errors


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    # os.rename(path, os.path.join(head, '.' + fn))


def parse_appsinstalled(line):
    line_parts = line.strip().split('\t')
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(',')]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(',') if a.isidigit()]
        logging.info('Not all user apps are digits: `%s`' % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info('Invalid geo coords: `%s`' % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def serialize_appsinstalled(appsinstalled):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = '%s:%s' % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    return (key, packed)


def file_handler(fn, options):
    device_memc = {
        'idfa': options.idfa,
        'gaid': options.gaid,
        'adid': options.adid,
        'dvid': options.dvid,
    }

    thread_pool = {}
    job_pool = {}
    result_queue = Queue()
    chunks = {}
    for dev_type, memc_addr in device_memc.items():
        memc = memcache.Client([memc_addr])
        job_pool[dev_type] = Queue()
        worker = MemcacheWriter(job_pool[dev_type], result_queue, memc, options.dry, options.attempts)
        thread_pool[dev_type] = worker
        chunks[dev_type] = {}
        worker.start()

    processed = errors = 0
    logging.info('[Worker %s] Processing %s' % (os.getpid(), fn))
    fd = gzip.open(fn)
    for line in fd:
        line = line.decode().strip()
        if not line:
            continue
        appsinstalled = parse_appsinstalled(line)
        if not appsinstalled:
            errors += 1
            continue
        dev_type = appsinstalled.dev_type
        if dev_type not in device_memc:
            errors += 1
            logging.error('Unknown device type: %s' % appsinstalled.dev_type)
            continue

        key, value = serialize_appsinstalled(appsinstalled)
        chunk = chunks[dev_type]
        chunk[key] = value
        if len(chunk.keys()) == CHUNK_SIZE:
            job_pool[dev_type].put(chunk)
            chunks[dev_type] = {}

    for dev_type, chunk in chunks.items():
        if chunk:
            job_pool[dev_type].put(chunk)

    for q in job_pool.values():
        q.put(SENTINEL)
    for t in thread_pool.values():
        t.join()
    while not result_queue.empty():
        result = result_queue.get(timeout=0.1)
        processed += result[0]
        errors += result[1]

    if not processed:
        fd.close()
        return fn

    err_rate = float(errors) / processed
    if err_rate < NORMAL_ERR_RATE:
        logging.info('Acceptable error rate (%s). Successfull load' % err_rate)
    else:
        logging.error('High error rate (%s > %s). Failed load' % (err_rate, NORMAL_ERR_RATE))
    fd.close()
    return fn


def main(options):
    pool = Pool(options.workers)
    process_args = ((file_name, options) for file_name in sorted(glob.iglob(options.pattern)))
    for fn in pool.starmap(file_handler, process_args):
        logging.info('Renaming %s' % fn)
        dot_rename(fn)


def prototest():
    sample = 'idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\n' \
             'gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424'
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split('\t')
        apps = [int(a) for a in raw_apps.split(',') if a.isdigit()]
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
    op.add_option('-t', '--test', action='store_true', default=False)
    op.add_option('-l', '--log', action='store', default=None)
    op.add_option('--dry', action='store_true', default=False)
    op.add_option('--pattern', action='store', default='/data/appsinstalled/*.tsv.gz')
    op.add_option('--idfa', action='store', default='127.0.0.1:33013')
    op.add_option('--gaid', action='store', default='127.0.0.1:33014')
    op.add_option('--adid', action='store', default='127.0.0.1:33015')
    op.add_option('--dvid', action='store', default='127.0.0.1:33016')
    op.add_option('-w', '--workers', action='store', type=int, default=cpu_count() + 1)
    op.add_option('-a', '--attempts', action='store', type=int, default=3)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info('Memc loader started with options: %s' % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception('Unexpected error: %s' % e)
        sys.exit(1)
