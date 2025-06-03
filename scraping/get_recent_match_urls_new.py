from camoufox.async_api import AsyncCamoufox
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
import asyncio
import time
import math


config = {
    "savefile_location": "data/recent_match_urls.csv",  # ".../.../example.csv" (file that will get created/updated when finished)
    "url_amount": 5000,  # -1 = all (NOT RECOMMENDED HERE) Note: Entered number will ALWAYS round up to the next hundreth (901 -> 1000)
    "headless": True,  # hide the browser
}

if config["url_amount"] > 0:
    config["url_amount"] = int(math.ceil(config["url_amount"] / 100.0) * 100)

recent_matches_url = "https://www.hltv.org/results"
match_urls = []  # List that gets turned into the savefile


class bcolors:  # colors to print in color
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    SUCCESS = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

def status(msg, color=bcolors.ENDC):
    print(color + msg + bcolors.ENDC)

async def scrape_match_urls(page, url, offset):
    start_time = time.perf_counter()
    offset_url = url + "?offset=" + str(offset)
    await page.goto(offset_url)
    html = await page.inner_html("div.results")
    soup = BeautifulSoup(html, "html.parser")

    recent_matches = soup.select_one("div.allres")
    new_urls = 0
    if recent_matches:
        result_con = recent_matches.select("div.result-con")
        before = len(match_urls)

        for match in result_con:
            result = match.find("a", href=True)
            if result:
                full_url = f"https://www.hltv.org{result['href']}"
                match_urls.append(full_url)
        after = len(match_urls)
        new_urls = after - before

    end_time = time.perf_counter()
    elapsed = end_time - start_time
    status(
        f"[+] {new_urls} URLs scraped! ({len(match_urls)} / {config["url_amount"]}) ({elapsed:.2f}s)",
        bcolors.SUCCESS,
    )


async def main():
    async with AsyncCamoufox(headless=config["headless"]) as browser:
        total_start_time = time.perf_counter()
        page = await browser.new_page()

        if config["url_amount"] == -1:
            status(
                "[!] Scraping all URLs (will probably take forever, not recommended)",
                bcolors.WARNING,
            )
        else:
            status(f"[!] Scraping {config["url_amount"]} URLs", bcolors.HEADER)

        for offset in range(0, config["url_amount"], 100):
            await scrape_match_urls(page, recent_matches_url, offset)

        end_time = time.perf_counter()
        total_elapsed = end_time - total_start_time

    await browser.close()

    final_df = pd.DataFrame(match_urls, columns=["match_url"])
    filepath = Path(config["savefile_location"])
    filepath.parent.mkdir(parents=True, exist_ok=True) # Creates directory if it's not existing
    # Change "to_csv" to something else to save it in a different format (need to change savefile ending too)
    final_df.to_csv(filepath, index=False)

    print(
        bcolors.SUCCESS
        + f"[+] Successfully saved to file ({config["savefile_location"]}) (took {total_elapsed:.2f}s)"
    )


if __name__ == "__main__":
    asyncio.run(main())