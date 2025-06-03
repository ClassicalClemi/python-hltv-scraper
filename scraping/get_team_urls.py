from camoufox.async_api import AsyncCamoufox
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
import asyncio
import time


config = {
    "savefile_location": "data/team_urls.csv",  # ".../.../example.csv" (file that will get created/updated when finished)
    "url_amount": -1,  # -1 = all (Recommended here)
    "headless": True,  # hide the browser
}

world_ranking_url = ("https://www.hltv.org/ranking/teams")  # automatically adds current date when opening
team_urls = []  # List that gets turned into the savefile


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


async def main():
    async with AsyncCamoufox(headless=config["headless"]) as browser:
        total_start_time = time.perf_counter()
        page = await browser.new_page()

        # Get HTML
        await page.goto(world_ranking_url)
        status(f"[+] Successfully opened URL ({world_ranking_url})", bcolors.SUCCESS)
        html = await page.inner_html("div.ranking")
        soup = BeautifulSoup(html, "html.parser")
        status(f"[+] Successfully parsed HTML", bcolors.SUCCESS)

        team_links = soup.select("a[href*='/team/']")

        for link in team_links[: config["url_amount"]]:
            href = link.get("href")
            if href and "/team/" in href:
                full_url = (
                    f"https://www.hltv.org{href}" if href.startswith("/") else href
                )
                team_urls.append(full_url)

        end_time = time.perf_counter()
        total_elapsed = end_time - total_start_time
    await browser.close()

    print(bcolors.SUCCESS + f"[+] Found Team-URLs: {len(team_urls)}")

    final_df = pd.DataFrame(team_urls, columns=["team_url"])
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
