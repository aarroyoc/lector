import feedparser
import boto3
from boto3.s3.transfer import S3Transfer
from jinja2 import Environment, FileSystemLoader, select_autoescape

import itertools
import json
import mimetypes
import shutil
import tempfile
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

# AWS_ACCESS_KEY=AKIASGL7DYLEIHSQONFB
# AWS_SECRET_ACCESS_KEY=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

@dataclass
class Item:
    title: str
    url: str
    date: datetime

    def __lt__(self, other):
        return self.date < other.date

    @staticmethod
    def from_feeditem(item):
        pdate = item["published_parsed"]
        published_date = datetime(year=pdate.tm_year, month=pdate.tm_mon, day=pdate.tm_mday)
        return Item(item["title"], item["link"], published_date)

    def is_in_last_month(self):
        return (datetime.today() - self.date).days < 30

def fetch_items(feed):
    all_items = map(Item.from_feeditem, feed["items"])
    return filter(lambda x: x.is_in_last_month(), all_items)

def handler(event, context):
    main()

def main():
    items = list()

    with open("rss.json") as f:
        rss = json.load(f)

    feeds = map(feedparser.parse, rss)
    items = map(fetch_items, feeds)
    items = itertools.chain(*items)
    items = list(items)

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

    s3 = boto3.client("s3")
    transfer = S3Transfer(s3)
    for path in output_folder.iterdir():
        transfer.upload_file(str(path), "lector.adrianistan.eu", path.name, extra_args={
            "ACL": "public-read",
            "ContentType": mimetypes.guess_type(path.name)[0]
        })

if __name__ == "__main__":
    main()