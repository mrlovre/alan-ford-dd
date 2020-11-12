import os
import re
import time
from pathlib import Path
from urllib import request
import skimage.io
import skimage.color
import skimage
import numpy as np
from PIL import Image, ImageEnhance
import itertools
from io import BytesIO
from multiprocessing import Pool

from bs4 import BeautifulSoup

# %%
home_url = "https://striputopija.blogspot.com/p/alan-ford.html"
soup = BeautifulSoup(request.urlopen(home_url), "html.parser")

# %%
subpages = soup.find_all("a", href=re.compile(r"striputopija.*201[0-9].*[0-9]{3}[-0-9]*\.html"))
subpages = [page for page in subpages if re.compile(r"[0-9]{3}\.").match(page.string or "")]

# %%
start = 1
end = 10
fails = []
for i in range(start, end + 1):
    try:
        missing_pages = False
        subpage = next(page for page in subpages if re.compile(rf".*/{i:03}.*\.html").match(page["href"] or ""))
        title = subpage.string
        subpage = BeautifulSoup(request.urlopen(subpage["href"]), "html.parser")
        pages = subpage.find("div", {"class": "post-body"}).find_all("a", href=re.compile(r"/s1600/.*\..*"))
        pages = [page["href"] for page in pages]
        print(f"Doing '{title}': ", end="")

        save_dir = f"_downloads/"
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        if Path(save_dir + f"{title}.pdf").exists():
            print("already done!")
            continue

        if not pages:
            raise RuntimeError()

        has_cover = False

        def download(url):
            global missing_pages
            try:
                if not url.startswith("https:"):
                    url = "https:" + url

                image = request.urlopen(url)
                image = Image.open(BytesIO(image.read()))
                if has_cover:
                    image = image.convert("L")
                    image = ImageEnhance.Contrast(image).enhance(2.0)
                return image
            except Exception as e:
                print(url)
                missing_pages = True
                return None

        pages = iter(pages)

        cover = None
        while cover is None:
            cover = download(next(pages))

        has_cover = True
        with Pool(8) as pool:
            images = pool.map(download, pages)

        images = [image for image in images if image]

        cover.save(save_dir + f"{title}.pdf", save_all=True, append_images=images)

        print("done!")
        if missing_pages:
            print("Possible missing pages.")
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(e)
        print("failed!")
        fails += [i]
