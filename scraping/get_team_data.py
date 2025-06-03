from camoufox.async_api import AsyncCamoufox
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
import asyncio
import time


config = {
    "file_to_read": "data/team_urls.csv",  # ".../.../example.csv" (file to read from, e.g. urls)
    "savefile_location": "data/team_data.csv",  # ".../.../example.csv" (file that will get created/updated when finished)
    "team_amount": -1,  # -1 = all
    "headless": True,  # hide the browser
}

df = pd.read_csv(config["file_to_read"])
team_data = []  # List that gets turned into the savefile


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
    player_links = soup.select("a[href*='/player/']")
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


async def main():
    async with AsyncCamoufox(headless=config["headless"]) as browser:
        total_start_time = time.perf_counter()
        page = await browser.new_page()

        if config["team_amount"] == -1:
            status(f"[!] Scraping all teams ({len(df["team_url"])})", bcolors.HEADER)
        else:
            status(f"[!] Scraping {config["team_amount"]} teams", bcolors.HEADER)

        for url in df["team_url"][: config["team_amount"]]:
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
                world_ranking_element.text.strip() if world_ranking_element else None
            )

            valve_ranking_element = soup.select_one("a[href*='/valve-ranking/teams']")
            valve_ranking = (
                valve_ranking_element.text.strip() if valve_ranking_element else None
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

            end_time = time.perf_counter()
            elapsed = end_time - start_time
            total_elapsed = end_time - total_start_time
            team_data.append(team_info)
            if config["team_amount"] == -1:
                status(
                    f"[+] Successfully scraped {team_info["team_name"]} ({team_info["world_ranking"]} World) ({len(team_data)} / {len(df["team_url"])}) ({elapsed:.2f}s)",
                    bcolors.SUCCESS,
                )
            else:
                status(
                    f"[+] Successfully scraped {team_info["team_name"]} ({team_info["world_ranking"]} World) ({len(team_data)} / {config["team_amount"]}) ({elapsed:.2f}s)",
                    bcolors.SUCCESS,
                )

    await browser.close()

    final_df = pd.DataFrame(team_data)
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
