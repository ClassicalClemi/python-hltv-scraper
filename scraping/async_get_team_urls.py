from camoufox.async_api import AsyncCamoufox
from browserforge.fingerprints import Screen
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
import asyncio
import random
import time
import json

config = {
    "savefile_location": "data/team_urls.csv",  # ".../.../example.csv" (file that will get created/updated when finished)
    "team_amount": -1,  # -1 = all (Recommended here)
    "headless": True,  # hide the browser
    "screen": Screen(max_width=1920, max_height=1080),
    # only 1 session is needed here (it's only one page to scrape)
    "use_proxy": False,  # use proxy
    "use_proxy_once": False,  # enable this to use a different proxy for each session (if you have enough proxies)
    "proxy_location": ".../.../proxies.txt",  # location of the proxy list (format: server:port:username:password), 1 every line
    "user_agents_location": ".../.../user_agents.json",  # location of the user agents list # refer to the readme for more info
    "cookie_location": ".../.../autologin_cookie.json",  # location of the cookies incl. autologin
}


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


world_ranking_url = (
    "https://www.hltv.org/ranking/teams"  # automatically adds current date when opening
)
team_urls = []  # List that gets turned into the savefile
lock = asyncio.Lock()  # lock for thread-safety when writing to data list

if config["use_proxy"]:
    proxy_list = []
    with open("rework/data/proxies.txt", "r") as file:
        for line in file:
            proxy_list.append(line.strip())


# Get random proxy from list
def get_proxy():
    proxy = random.choice(proxy_list)
    if config["use_proxy_once"]:
        proxy_list.remove(proxy)
    proxy = proxy.split(":")
    server = proxy[0] + ":" + proxy[1]
    username = proxy[2]
    password = proxy[3]
    proxy_dict = {"server": server, "username": username, "password": password}
    return proxy_dict


async def scrape_team_urls(session_id, headless, url):
    proxy = get_proxy() if config["use_proxy"] else None
    async with AsyncCamoufox(
        headless=headless,
        screen=config["screen"],
        geoip=True,
        proxy=proxy,
    ) as browser:
        context = await browser.new_context()
        status(
            f"[+] [Session {session_id}] Successfully connected with proxy ({proxy['server']})",
            bcolors.OKCYAN,
        )

        # User-Agent rotation (https://www.useragents.me/#most-common-desktop-useragents-json-csv)
        with open(config["user_agents_location"], "r") as f:
            user_agents = json.load(f)
        user_agent_entry = random.choice(user_agents)
        user_agent = user_agent_entry["ua"]
        await context.set_extra_http_headers({"User-Agent": user_agent})

        # Auto-login & add necessary cookies
        with open(config["cookie_location"], "r") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)

        page = await context.new_page()

        try:
            start_time = time.perf_counter()
            await page.goto(url)

            # Get HTML
            status(
                f"[+] [Session {session_id}] Successfully opened URL ({world_ranking_url})",
                bcolors.SUCCESS,
            )
            html = await page.inner_html("div.ranking")
            soup = BeautifulSoup(html, "html.parser")
            status(
                f"[+] [Session {session_id}] Successfully parsed HTML", bcolors.SUCCESS
            )

            team_links = soup.select("a[href*='/team/']")

            for link in team_links[: config["team_amount"]]:
                href = link.get("href")
                if href and "/team/" in href:
                    full_url = (
                        f"https://www.hltv.org{href}" if href.startswith("/") else href
                    )
                    # thread-safe
                    async with lock:
                        if full_url not in team_urls:
                            team_urls.append(full_url)

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            status(
                f"[+] [Session {session_id}] Found Team-URLs: {len(team_urls)} ({elapsed:.2f}s)",
                bcolors.SUCCESS,
            )

        except Exception as e:
            status(
                f"[-] Session {session_id}: Exception - {e}",
                bcolors.FAIL,
            )
            return  # or break


async def main():
    total_start_time = time.perf_counter()

    if config["team_amount"] == -1:
        status(
            "[!] Scraping all teams (recommended)",
            bcolors.WARNING,
        )
    else:
        status(
            f"[!] Scraping {config['team_amount']} teams (scraping all teams is recommended)",
            bcolors.WARNING,
        )

    task = asyncio.create_task(
        scrape_team_urls(
            session_id=0, headless=config["headless"], url=world_ranking_url
        )
    )
    await task

    total_elapsed = time.perf_counter() - total_start_time

    final_df = pd.DataFrame(team_urls, columns=["team_url"])
    filepath = Path(config["savefile_location"])
    # Creates directory if it's not existing
    filepath.parent.mkdir(parents=True, exist_ok=True)
    # Change "to_csv" to something else to save it in a different format (need to change savefile ending too)
    final_df.to_csv(filepath, index=False)

    status(
        f"[+] Successfully saved to file ({config["savefile_location"]}) (took {total_elapsed:.2f}s)",
        bcolors.SUCCESS,
    )


if __name__ == "__main__":
    asyncio.run(main())
