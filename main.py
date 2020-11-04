import aiohttp
import feedparser
import boto3
from boto3.s3.transfer import S3Transfer
from jinja2 import Environment, FileSystemLoader, select_autoescape

import asyncio
import itertools
import xml.etree.ElementTree as ET
import logging
import mimetypes
import shutil
import urllib
import tempfile
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

logging.getLogger().setLevel(logging.INFO)

# Sequential 2:50
# Aiohttp: 1.17

@dataclass
class Item:
    title: str
    url: str
    date: datetime
    source: str


    def __lt__(self, other):
        return self.date < other.date

    @property
    def readable_date(self):
        return self.date.strftime("%d/%m/%Y")

    @staticmethod
    def from_feeditem(item, source):
        try:
            pdate = item.get("published_parsed", item.get("updated_parsed"))
            published_date = datetime(year=pdate.tm_year, month=pdate.tm_mon, day=pdate.tm_mday)
            return Item(item["title"], item["link"], published_date, source)
        except:
            return None

    def is_in_last_month(self):
        return (datetime.today() - self.date).days < 30

def fetch_items(feed, source):
    all_items = map(lambda x: Item.from_feeditem(x, source), feed["items"])
    all_items = filter(lambda x: x is not None, all_items)
    return filter(lambda x: x.is_in_last_month(), all_items)

def parse_source(feed_text, source):
    feed = feedparser.parse(feed_text)
    if feed.bozo == 0 or type(feed.bozo_exception) != urllib.error.URLError:
        return fetch_items(feed, source)
    else:
        logging.error(f"Feed '{source}' is not available")
        return []

def handler(event, context):
    asyncio.run(main())

async def main():
    tree = ET.parse("sources.opml")
    body = tree.find("body")

    sources = [ outline.get("title") for outline in body.iter("outline")]
    feeds_url = [ outline.get("xmlUrl") for outline in body.iter("outline")]

    items = list()

    async with aiohttp.ClientSession() as session:
        feeds = [session.get(url) for url in feeds_url]
        for feed_task in asyncio.as_completed(feeds):
            try:
                feed = await feed_task
                url = str(feed.url)
                logging.info(f"Downloaded {url} with success")
                feed_text = await feed.text()
                i = feeds_url.index(url)
                source = sources[i]
                items.extend(parse_source(feed_text, source))
            except:
                pass

    env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(["html"])
    )

    items.sort(reverse=True)

    temp_dir = tempfile.mktemp()
    output_folder = Path(temp_dir) / "_site"
    if not output_folder.exists():
        output_folder.mkdir(parents=True)

    output_file = output_folder / "index.html"

    static_folder = Path.cwd() / "static"
    shutil.copytree(static_folder, output_folder, dirs_exist_ok=True)

    with open(output_file, "w") as f:
        f.write(env.get_template("index.html").render(items=items))

    print(f"OK: {output_folder}")

    s3 = boto3.client("s3")
    transfer = S3Transfer(s3)
    for path in output_folder.iterdir():
        transfer.upload_file(str(path), "lector.adrianistan.eu", path.name, extra_args={
            "ACL": "public-read",
            "ContentType": mimetypes.guess_type(path.name)[0]
        })

if __name__ == "__main__":
    asyncio.run(main())