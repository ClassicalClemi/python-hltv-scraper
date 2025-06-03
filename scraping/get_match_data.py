from camoufox.async_api import AsyncCamoufox
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
import asyncio
import time
import re


config = {
    "file_to_read": "data/recent_match_urls.csv",  # ".../.../example.csv" (file to read from, e.g. urls)
    "savefile_location": "data/recent_match_data.csv",  # ".../.../example.csv" (file that will get created/updated when finished)
    "match_amount": 10,  # -1 = all Note: This will probably take a REALLY long time, depending on url amount
    "headless": True,  # hide the browser
}

df = pd.read_csv(config["file_to_read"])
match_data = []  # List that gets turned into the savefile


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

def get_team(soup, team_number):
    teamsBox = soup.select_one("div.teamsBox")

    if teamsBox:
        if team_number == 1:
            team_name = teamsBox.select_one("div.team1-gradient div.teamName")
            if team_name:
                return team_name.text.strip().replace(" ", "")

        if team_number == 2:
            team_name = teamsBox.select_one("div.team2-gradient div.teamName")
            if team_name:
                return team_name.text.strip().replace(" ", "")

def get_score(soup, team_number):
    teamsBox = soup.select_one("div.teamsBox")

    if teamsBox:
        if team_number == 1:
            score = teamsBox.select_one(
                "div.team1-gradient div.lost, div.team1-gradient div.won"
            )
            if score:
                return score.text.strip()

        if team_number == 2:
            score = teamsBox.select_one(
                "div.team2-gradient div.lost, div.team2-gradient div.won"
            )
            if score:
                return score.text.strip()

def get_winner(soup, team_1, team_2):
    teamsBox = soup.select_one("div.teamsBox")

    team_1_gradient = teamsBox.select_one("div.team1-gradient")
    team_2_gradient = teamsBox.select_one("div.team2-gradient")

    if team_1_gradient and "won" in team_1_gradient.get("class", []):
        score = team_1
    elif team_2_gradient and "won" in team_2_gradient.get("class", []):
        score = team_2
    elif team_1_gradient.select_one("div.won"):
        score = team_1
    elif team_2_gradient.select_one("div.won"):
        score = team_2

    if teamsBox and score:
        return score

def get_date(soup):
    timeAndEvent = soup.select_one("div.timeAndEvent")

    if timeAndEvent:
        date_text = timeAndEvent.select_one("div.date").text.strip()

        if date_text:
            # Replace (st, nd, rd, th)
            date_text = (
                date_text.replace("st", "")
                .replace("nd", "")
                .replace("rd", "")
                .replace("th", "")
            )

            # Replace "of"
            date_text = date_text.replace(" of ", " ")

            # Month to number
            months = {
                "January": "01",
                "February": "02",
                "March": "03",
                "April": "04",
                "May": "05",
                "June": "06",
                "July": "07",
                "August": "08",
                "September": "09",
                "October": "10",
                "November": "11",
                "December": "12",
            }

            # "1 June 2025" -> ["1", "June", "2025"]
            parts = date_text.split()
            day = parts[0].zfill(2)  # add 0 if needed
            month = months[parts[1]]
            year = parts[2]

            return f"{day}/{month}/{year}"

def get_hour(soup):
    timeAndEvent = soup.select_one("div.timeAndEvent")
    if timeAndEvent:
        time = timeAndEvent.select_one("div.time").text.strip()
        if time:
            hour = time.split(":")[0]
            return hour

def get_event(soup):
    timeAndEvent = soup.select_one("div.timeAndEvent")
    if timeAndEvent:
        event = timeAndEvent.select_one("a[href*='/events/']").text.strip()
        if event:
            return event

def get_mode(soup):
    maps = soup.select_one("div.maps")
    if maps:
        mode = maps.select_one("div.preformatted-text").text.strip()
        if mode:
            numbers = re.findall(r"\d+", mode)
            if numbers:
                num = numbers[0]  # First number found
                return f"Bo{num}"
    return "N/A"

def get_maps_info(soup, team_1, team_2):
    maps_list = []
    maps_grid = soup.select_one("div.maps")
    if maps_grid:
        maps = maps_grid.select("div.mapholder")
        if maps:
            for map in maps:
                if map.select("div.played"):
                    map_info = {}

                    map_info["map"] = map.select_one("div.mapname").text.strip()

                    results_left = map.select_one("div.results-left, span.results-left")
                    results_right = map.select_one(
                        "div.results-right, span.results-right"
                    )

                    if results_left and "pick" in results_left.get("class", []):
                        map_info["picked_by"] = team_1
                    elif results_right and "pick" in results_right.get("class", []):
                        map_info["picked_by"] = team_2
                    else:
                        map_info["picked_by"] = "N/A"

                    if results_left and "won" in results_left.get("class", []):
                        map_info["winner"] = team_1
                    elif results_right and "won" in results_right.get("class", []):
                        map_info["winner"] = team_2
                    else:
                        map_info["winner"] = "N/A"

                    if results_left:
                        score_left = results_left.select_one(
                            "div.results-team-score"
                        ).text.strip()
                    if results_right:
                        score_right = results_right.select_one(
                            "div.results-team-score"
                        ).text.strip()

                    if score_left and score_right:
                        map_info["score"] = f"{score_left}:{score_right}"

                    maps_list.append(map_info)

    return maps_list


async def main():
    async with AsyncCamoufox(headless=config["headless"]) as browser:
        total_start_time = time.perf_counter()
        page = await browser.new_page()

        if config["match_amount"] == -1:
            status(
                f"[!] Scraping all matches ({len(df["match_url"])})",
                bcolors.HEADER,
            )
        else:
            status(f"[!] Scraping {config["match_amount"]} matches", bcolors.HEADER)

        for url in df["match_url"][: config["match_amount"]]:
            start_time = time.perf_counter()

            # Get HTML
            await page.goto(url)
            html = await page.inner_html("div.colCon")
            soup = BeautifulSoup(html, "html.parser")

            team_1 = get_team(soup, 1)
            team_2 = get_team(soup, 2)
            score_team_1 = get_score(soup, 1)
            score_team_2 = get_score(soup, 2)
            winner = get_winner(soup, team_1, team_2)
            date = get_date(soup)
            hour = get_hour(soup)
            event = get_event(soup)
            mode = get_mode(soup)
            maps = get_maps_info(soup, team_1, team_2)

            match_info = {
                # "match_url": url,
                "team_1": team_1,
                "team_2": team_2,
                "score_team_1": score_team_1,
                "score_team_2": score_team_2,
                "winner": winner,
                "date": date,
                "hour": hour,
                "event": event,
                "mode": mode,
                "maps": maps,
            }

            """
            "maps": [
                {"map": "Dust2", "picked_by": "team_1", "winner": "team_1", "score": "16-14"},
                {"map": "Mirage", "picked_by": "team_2", "winner": "team_2", "score": "16-12"},
                {"map": "Inferno", "picked_by": "random", "winner": "team_1", "score": "16-10"}
            ]
            """

            match_data.append(match_info)
            end_time = time.perf_counter()
            elapsed = end_time - start_time
            status(
                f"[+] Successfully scraped match: {team_1} vs {team_2} ({date}) ({len(match_data)} / {config["match_amount"]}) ({elapsed:.2f}s)",
                bcolors.SUCCESS,
            )

        end_time = time.perf_counter()
        total_elapsed = end_time - total_start_time

    await browser.close()

    final_df = pd.DataFrame(match_data)
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
