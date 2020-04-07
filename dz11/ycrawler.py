import os
import re
from urllib.parse import urlparse

import aiohttp
import asyncio
import logging
import argparse

from bs4 import BeautifulSoup
from collections import namedtuple
from mimetypes import guess_extension
from concurrent.futures import ThreadPoolExecutor

BASE_URL = 'https://news.ycombinator.com'
POST_URL = '{}/item?id={}'.format(BASE_URL, '{}')
OUTPUT_FOLDER = 'data'
URL_PATTERN = re.compile(r'^https?://')
INTERVAL = 30
LIMIT_PER_HOST = 3
REQUEST_TIMEOUT = 10
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'}
Post = namedtuple('Post', ['id', 'title', 'url'])
HttpResponse = namedtuple('HttpResponse', ['content', 'ext'])


async def fetch(url):
    if not URL_PATTERN.match(url):
        url = '{}/{}'.format(BASE_URL, url)
    logging.debug('Download url: {}'.format(url))
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    connector = aiohttp.TCPConnector(limit_per_host=LIMIT_PER_HOST, ssl=False)
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS, connector=connector) as session:
            async with session.get(url) as response:
                content = await response.text(encoding='utf-8')
                return HttpResponse(content, guess_extension(response.content_type))
    except Exception as e:
        logging.error('Download error: {} [{}]'.format(url, e))
        raise


def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)


async def download_page(url, file_dir, file_name):
    response = await fetch(url)
    path = "/".join((file_dir, file_name + response.ext))
    try:
        with ThreadPoolExecutor() as pool:
            await asyncio.get_running_loop().run_in_executor(pool, write_file, str(path), response.content)
    except OSError:
        logging.error('Can\'t save file: {}'.format(path))
    return response


def parse_main_page(html: str):
    posts = []
    soup = BeautifulSoup(html, "lxml")
    trs = soup.select("table.itemlist tr.athing")
    for index, tr in enumerate(trs):
        id, url, title = "", "", ""
        try:
            id = int(tr.attrs["id"])
            url = tr.select_one("td.title a.storylink").attrs["href"]
            title = tr.select_one("td.title a.storylink").text
            posts.append(Post(id=id, title=title, url=url))
        except KeyError:
            logging.info('Error on {} post (id: {}, url: {}, title: {})'.format(index, id, url, title))
            continue

    return posts


def parse_comments(content: str):
    links = set()
    soup = BeautifulSoup(content, "lxml")
    for link in soup.select(".comment a[rel=nofollow]"):
        url = link.attrs["href"]
        parsed_url = urlparse(url)
        if parsed_url.scheme and parsed_url.netloc:
            links.add(url)
    return list(links)


async def handle_comments(post_id, post_dir):
    response = await download_page(POST_URL.format(post_id), post_dir, 'item')
    links = parse_comments(response.content)
    logging.debug('Handle comments for {}: {} links'.format(post_id, len(links)))

    tasks = [
        asyncio.create_task(download_page(link, post_dir, 'link_{}'.format(idx)))
        for idx, link in enumerate(links, 1)
    ]
    await asyncio.gather(*tasks)


async def handle_post(post, output_dir):
    logging.debug('Handle post: {} (ID {})'.format(post.title, post.id))
    post_dir = '{}/{}'.format(output_dir, post.id)
    if not os.path.exists(post_dir):
        os.mkdir(post_dir)

    await asyncio.gather(*[download_page(post.url, post_dir, 'post'), handle_comments(post.id, post_dir), ])


async def handle_main_page(output_dir):
    response = await download_page(BASE_URL, output_dir, 'main')
    content = response.content

    posts = [
        post for post in parse_main_page(content)
    ]
    logging.info('Handle main page')

    tasks = []
    for post in posts:
        tasks.append(asyncio.create_task(handle_post(post, output_dir)))
    await asyncio.gather(*tasks)


async def main(output_folder, interval):
    while True:
        try:
            await asyncio.wait_for(handle_main_page(output_folder), timeout=interval)
        except Exception as e:
            logging.error('Crawler failed: {}'.format(e))
        await asyncio.sleep(interval)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='news.ycombinator.com interval crawler')
    parser.add_argument('-o', '--output', type=str, default=OUTPUT_FOLDER, help='Output folder')
    parser.add_argument('-i', '--interval', type=int, default=INTERVAL, help='Check interval in seconds')
    parser.add_argument('-d', '--debug', action='store_true', help='Show debug messages')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format='PID %(process)5s [%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    if not os.path.exists(args.output):
        os.mkdir(args.output)

    try:
        asyncio.run(main(args.output, args.interval))
    except KeyboardInterrupt:
        logging.info('Crawler stopped by KeyboardInterrupt')
