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
    "file_to_read": "data/team_urls.csv",  # ".../.../example.csv" (file to read from, e.g. urls)
    "savefile_location": "data/team_data.csv",  # ".../.../example.csv" (file that will get created/updated when finished)
    "team_amount": 100,  # -1 = all
    "headless": True,  # hide the browser
    "screen": Screen(max_width=1920, max_height=1080),
    "screen_amount": 1,  # only matters if headless = False
    "session_amount": 2,  # amount of parallel sessions (you will get rate limited if you set this too high)
    "session_timeout": 1,  # timeout between sessions ([0.8, 1.2] also possible for a random timeout in a range)
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


df = pd.read_csv(config["file_to_read"])
team_data = []  # List that gets turned into the savefile
lock = asyncio.Lock()  # lock for thread-safety when writing to data list

if config["use_proxy"]:
    proxy_list = []
    with open(config["proxy_location"], "r") as file:
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


def get_avg_player_age(soup):
    team_stats = soup.select("div.profile-team-stat")

    for stat in team_stats:
        b_tag = stat.find("b")
        if b_tag and "Average player age" in b_tag.text:
            age = stat.select_one("span.right")
            if age:
                return age.text
            break


def get_player_urls(soup):
    team_container = soup.select_one("div.bodyshot-team-bg")
    player_links = team_container.select("a[href*='/player/']")
    player_urls = []
    for link in player_links:
        if link:
            href = link.get("href")
            if href and "/player/" in href:
                full_url = (
                    f"https://www.hltv.org{href}" if href.startswith("/") else href
                )
                player_urls.append(full_url)
    return player_urls


def get_coach_url(soup):
    coach_link = soup.select_one("a[href*='/coach/']")
    if coach_link:
        href = coach_link.get("href")
        if href and "/coach/" in href:
            full_url = f"https://www.hltv.org{href}" if href.startswith("/") else href
            return full_url


def get_winstreak(soup):
    matchesBox = soup.select_one("#matchesBox")
    if matchesBox:
        highlighted_stats = matchesBox.select("div.highlighted-stat")

        for stat in highlighted_stats:
            description = stat.find("div", class_="description")
            if description and "Current win streak" in description.text:
                stat_value = stat.find("div", class_="stat")
                if stat_value:
                    return stat_value.text


def get_winrate(soup):  # from last 3 months
    matchesBox = soup.select_one("#matchesBox")
    if matchesBox:
        highlighted_stats = matchesBox.select("div.highlighted-stat")

        for stat in highlighted_stats:
            description = stat.find("div", class_="description")
            if description and "Win rate" in description.text:
                stat_value = stat.find("div", class_="stat")
                if stat_value:
                    return stat_value.text.replace("%", "")


# improvement possible, only scrapes winrate of best 6 maps on team profile
def get_map_winrate(soup, map):
    map_statistics = soup.select_one("div.map-statistics")
    if map_statistics:
        map_statistics_container = map_statistics.select("div.map-statistics-container")

        for container in map_statistics_container:
            map_element = container.select_one("div.map-statistics-row-map-mapname")
            if map_element:
                map_name = map_element.text.strip()

                if map_name == map:
                    winrate_element = container.select_one(
                        "div.map-statistics-row-win-percentage"
                    )
                    if winrate_element:
                        return winrate_element.text.replace("%", "").strip()

    return None  # if map is not in the best 6


async def scrape_team(session_id, headless, url_list):
    proxy = get_proxy() if config["use_proxy"] else None
    async with AsyncCamoufox(
        headless=headless,
        screen=config["screen"],
        geoip=True,
        proxy=proxy,
    ) as browser:
        context = await browser.new_context()
        if config["use_proxy"]:
            status(
                f"[+] [Session {session_id}] Successfully connected with proxy ({proxy['server']})",
                bcolors.OKCYAN,
            )
        else:
            status(
                f"[+] [Session {session_id}] Successfully started without proxy",
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

        for url in url_list:
            try:
                start_time = time.perf_counter()

                # Get HTML
                await page.goto(url)
                html = await page.inner_html("div.colCon")
                soup = BeautifulSoup(html, "html.parser")

                team_name_element = soup.select_one("h1.profile-team-name")
                team_name = (
                    team_name_element.text.strip().replace(" ", "")
                    if team_name_element
                    else None
                )

                team_region_element = soup.select_one("div.team-country")
                team_region = (
                    team_region_element.text.strip() if team_region_element else None
                )

                world_ranking_element = soup.select_one("a[href*='/ranking/teams/']")
                world_ranking = (
                    world_ranking_element.text.strip()
                    if world_ranking_element
                    else None
                )

                valve_ranking_element = soup.select_one(
                    "a[href*='/valve-ranking/teams']"
                )
                valve_ranking = (
                    valve_ranking_element.text.strip()
                    if valve_ranking_element
                    else None
                )

                average_age = get_avg_player_age(soup)
                player_urls = get_player_urls(soup)
                coach_url = get_coach_url(soup)
                current_winstreak = get_winstreak(soup)
                winrate = get_winrate(soup)  # from last 3 months

                map_winrates = {  # only 6 best maps get scraped
                    "Ancient": get_map_winrate(soup, "Ancient"),
                    "Anubis": get_map_winrate(soup, "Anubis"),
                    "Dust2": get_map_winrate(soup, "Dust2"),
                    "Inferno": get_map_winrate(soup, "Inferno"),
                    "Mirage": get_map_winrate(soup, "Mirage"),
                    "Nuke": get_map_winrate(soup, "Nuke"),
                    "Overpass": get_map_winrate(soup, "Overpass"),
                    "Train": get_map_winrate(soup, "Train"),
                    "Vertigo": get_map_winrate(soup, "Vertigo"),
                }

                team_info = {
                    # "team_url": url,
                    "team_name": team_name,
                    "team_region": team_region,
                    "world_ranking": world_ranking,
                    "valve_ranking": valve_ranking,
                    "avg_player_age": average_age,
                    "current_winstreak": current_winstreak,
                    "winrate": winrate,
                    "map_winrates": map_winrates,
                    "coach_url": coach_url,
                    "player_urls": player_urls,
                }

                # thread-safe
                async with lock:
                    if team_info not in team_data:
                        team_data.append(team_info)

                end_time = time.perf_counter()
                elapsed = end_time - start_time

                if config["team_amount"] == -1:
                    status(
                        f"[+] [Session {session_id}] Successfully scraped {team_info["team_name"]} ({team_info["world_ranking"]} World) ({len(team_data)} / {len(df["team_url"])}) ({elapsed:.2f}s)",
                        bcolors.SUCCESS,
                    )
                else:
                    status(
                        f"[+] [Session {session_id}] Successfully scraped {team_info["team_name"]} ({team_info["world_ranking"]} World) ({len(team_data)} / {config["team_amount"]}) ({elapsed:.2f}s)",
                        bcolors.SUCCESS,
                    )

                if type(config["session_timeout"]) == list:
                    await asyncio.sleep(
                        random.uniform(
                            config["session_timeout"][0], config["session_timeout"][1]
                        )
                    )
                else:
                    await asyncio.sleep(config["session_timeout"])

            except Exception as e:
                status(
                    f"[-] Session {session_id}: Exception - {e}",
                    bcolors.FAIL,
                )
                return  # or break


def distribute_urls(
    df, team_amount=config["team_amount"], session_amount=config["session_amount"]
):
    # Create a list of empty lists for each session
    url_lists = [[] for _ in range(session_amount)]

    # Get all URLs
    urls = df["team_url"].tolist()

    # Distribute the URLs evenly across the sessions
    for url in urls[:team_amount]:
        smallest_list = min(url_lists, key=len)
        smallest_list.append(url)

    return url_lists


async def main():
    total_start_time = time.perf_counter()

    if config["team_amount"] == -1:
        status(
            f"[!] Scraping all teams ({len(df["team_url"])})",
            bcolors.WARNING,
        )
    else:
        status(f"[!] Scraping {config["team_amount"]} teams", bcolors.WARNING)

    urls_per_session = distribute_urls(
        df, config["team_amount"], config["session_amount"]
    )

    tasks = []
    for i in range(config["session_amount"]):

        if not config["headless"]:
            is_headless = False if i < config["screen_amount"] else True
        else:
            is_headless = True

        tasks.append(
            asyncio.create_task(
                scrape_team(
                    session_id=i,
                    headless=is_headless,
                    url_list=urls_per_session[i],
                )
            )
        )

    await asyncio.gather(*tasks)

    total_elapsed = time.perf_counter() - total_start_time

    final_df = pd.DataFrame(team_data)
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
