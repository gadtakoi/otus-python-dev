#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import appsinstalled_pb2
import memcache

NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])
FINISH = 'finish'


def dot_rename(path):
    print('path============', path)
    head, fn = os.path.split(path)
    # atomic in most cases
    # os.rename(path, os.path.join(head, "." + fn))


def insert_appsinstalled(memc, appsinstalled, dry_run=False):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    # @TODO persistent connection
    # @TODO retry and timeouts!
    try:
        if dry_run:
            logging.debug("%s - %s -> %s" % (memc, key, str(ua).replace("\n", " ")))
        else:
            # memc = memcache.Client([memc_addr])
            memc.set(key, packed)
    except Exception as e:
        logging.exception("Cannot write to memc %s: %s" % (memc, e))
        return False
    return True


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
    def __init__(self, job_pool, memc, results_queue):
        super().__init__()
        self.job_pool = job_pool
        self.memc = memc

    def run(self) -> None:
        processed = 0
        errors = 0
        while True:
            try:
                line = self.job_pool.get(timeout=0.1)
                print('line====', line)
                if line == FINISH:
                    self.job_pool.task_done()
                    break
                else:
                    processed += 1
                    if not insert_appsinstalled(self.memc, line):
                        errors += 1

                    # appsinstalled = parse_appsinstalled(line)
                    # print('appsinstalled====', appsinstalled)
                    # insert_appsinstalled(self.memc, appsinstalled)
                    # proc_items, err_items = self.insert_appsinstalled(chunks)
                    # print('self.memc=============', self.memc)
                    # proc_items, err_items = insert_appsinstalled(self.memc, line)
                    # processed += proc_items
                    # errors += err_items
                    self.job_pool.task_done()
            except Empty:
                continue


def file_handler(fn, options, device_memc):
    # print(fn, device_memc)
    jobs_pool = {}
    treads_pool = list()
    results_queue = Queue()
    for dev_type, address in device_memc.items():
        # print(dev_type, address)
        memc = memcache.Client(servers=[address])
        jobs_pool[dev_type] = Queue()
        thread = Worker(jobs_pool[dev_type], memc, results_queue)
        treads_pool.append(thread)
        thread.start()

    processed = errors = 0
    logging.info('Processing %s' % fn)
    fd = gzip.open(fn)

    for line in fd:
        line = line.decode().strip()
        if not line:
            continue
        print('line2=', line)
        appsinstalled = parse_appsinstalled(line)
        print('appsinstalled==================', appsinstalled)
        jobs_pool[appsinstalled.dev_type].put(appsinstalled)

        # if not appsinstalled:
        #     errors += 1
        #     continue
        # memc_addr = device_memc.get(appsinstalled.dev_type)
        # if not memc_addr:
        #     errors += 1
        #     logging.error("Unknown device type: %s" % appsinstalled.dev_type)
        #     continue

    for d_type in device_memc:
        jobs_pool[d_type].put(FINISH)

    for tp in treads_pool:
        tp.join()

    if not processed:
        fd.close()
        # continue

    # err_rate = float(errors) / processed
    # if err_rate < NORMAL_ERR_RATE:
    #     logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
    # else:
    #     logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
    fd.close()
    # dot_rename(fn)
    return fn


def main(options):
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    pool = Pool(cpu_count())

    process_args = ((fn, options, device_memc) for fn in sorted(glob.iglob(options.pattern)))
    for file_name in pool.starmap(file_handler, process_args):
        dot_rename(file_name)


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
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
