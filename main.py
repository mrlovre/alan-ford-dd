import os
import re
import time
from pathlib import Path
from urllib import request
import skimage.io
import skimage.color
import skimage
import numpy as np
import PIL
from PIL import Image, ImageEnhance
from skimage.transform import rescale
import itertools
from io import BytesIO
from multiprocessing import Pool

from bs4 import BeautifulSoup
import img2pdf

# %%
home_url = "https://striputopija.blogspot.com/p/alan-ford.html"
soup = BeautifulSoup(request.urlopen(home_url), "html.parser")

# %%
subpages = soup.find_all("a", href=re.compile(r"striputopija.*201[0-9].*[0-9]{3}[-0-9]*\.html"))
subpages = [page for page in subpages if re.compile(r"[0-9]{3}\.").match(page.string or "")]

# %%
start = 75
end = 200
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
                    width, height = image.size

                    image = image.convert("L")
                    image = image.resize((4 * width // 2, 4 * height // 2), resample=PIL.Image.BICUBIC)
                    image = ImageEnhance.Contrast(image).enhance(100.0)
                    image = image.convert("1")

                out = BytesIO()
                image.save(out, "tiff" if has_cover else "png")

                return out.getvalue()

            except Exception as e:
                print(e, url)
                missing_pages = True
                return None

        pages = iter(pages)

        cover = None

        if i == 61:  # bugfix
            next(pages)

        while cover is None:
            cover = download(next(pages))

        has_cover = True

        with Pool(8) as pool:
            images = pool.map(download, pages)

        images = [image for image in images if image]

        # cover.save(save_dir + f"{title}.pdf", save_all=True, append_images=images)
        with open(save_dir + f"{title}.pdf", "wb") as file:
            file.write(img2pdf.convert([cover] + images))

        print("done!")
        if missing_pages:
            print("Possible missing pages.")

    except KeyboardInterrupt:
        raise

    except Exception as e:
        print(e)
        print("failed!")
        fails += [i]
