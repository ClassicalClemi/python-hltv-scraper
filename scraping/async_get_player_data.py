from dateutil.relativedelta import relativedelta
from camoufox.async_api import AsyncCamoufox
from browserforge.fingerprints import Screen
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
import asyncio
import random
import time
import json
import ast
import re

config = {
    "file_to_read": "data/team_data.csv",  # ".../.../example.csv" (file to read from, e.g. urls)
    "savefile_location": "data/player_data.csv",  # ".../.../example.csv" (file that will get created/updated when finished)
    "team_amount": 10,  # -1 = all # Amount of teams of which the players will get scraped, basically multiply it by 5 to get player amount
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
player_data = []  # List that gets turned into the savefile
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


def update_player_url(
    player_url,
):
    end_date = datetime.today()
    start_date = end_date - relativedelta(months=3)
    end_str = end_date.strftime("%Y-%m-%d")
    start_str = start_date.strftime("%Y-%m-%d")

    parts = player_url.split("/")
    if parts:
        player_id = parts[4]
        player_name = parts[5]
        stats_url = f"https://www.hltv.org/stats/players/{player_id}/{player_name}?startDate={start_str}&endDate={end_str}"
        if stats_url:
            return stats_url


def get_overall_stats(soup):

    featured_rows = soup.select("div.summaryStatBreakdownRow")
    featured_stats_1 = featured_rows[0].select("div.summaryStatBreakdown")
    featured_stats_2 = featured_rows[1].select("div.summaryStatBreakdown")

    rating = featured_stats_1[0].select_one("div.summaryStatBreakdownDataValue").text
    dpr = featured_stats_1[1].select_one("div.summaryStatBreakdownDataValue").text
    kast = (
        featured_stats_1[2]
        .select_one("div.summaryStatBreakdownDataValue")
        .text.replace("%", "")
    )
    impact = featured_stats_2[0].select_one("div.summaryStatBreakdownDataValue").text

    stats_rows = soup.select("div.stats-rows")
    stats_1 = stats_rows[0].select("div.stats-row")
    stats_2 = stats_rows[1].select("div.stats-row")

    kills = stats_1[0].select("span")[1].text
    hs_percentage = stats_1[1].select("span")[1].text.replace("%", "")
    deaths = stats_1[2].select("span")[1].text
    kd = stats_1[3].select("span")[1].text
    adr = stats_1[4].select("span")[1].text
    grenade_adr = stats_1[5].select("span")[1].text
    maps_played = stats_1[6].select("span")[1].text

    rounds_played = stats_2[0].select("span")[1].text
    kr = stats_2[1].select("span")[1].text
    ar = stats_2[2].select("span")[1].text
    dr = stats_2[3].select("span")[1].text
    sbtr = stats_2[4].select("span")[1].text
    str = stats_2[5].select("span")[1].text

    overall = {
        "rating": rating,  # Rating 2.1
        "dpr": dpr,  # Deaths per round
        "kast": kast,  # Percentage of rounds in which the player either had a kill, assist, survived or was traded
        "impact": impact,  # Measures the impact made from multikills, opening kills, and clutches
        "kills": kills,
        "hs_percentage": hs_percentage,
        "deaths": deaths,
        "kd": kd,  # Kills / Deaths
        "adr": adr,  # Average Damage per Round
        "grenade_adr": grenade_adr,
        "maps_played": maps_played,
        "rounds_played": rounds_played,
        "kpr": kr,  # Kills / Round
        "apr": ar,  # Assists / Round
        "dpr": dr,  # Deaths / Round
        "saved_by_teammates_pr": sbtr,  # Saved by teammates / round
        "saved_teammates_pr": str,  # Saved teammates / round
    }

    return overall


async def get_individual_stats(page, url):
    await page.goto(url)
    html = await page.inner_html("div.columns")
    soup = BeautifulSoup(html, "html.parser")

    stats_rows = soup.select("div.stats-rows")
    boxes_1 = stats_rows[0].select("div.standard-box")
    boxes_2 = stats_rows[1].select("div.standard-box")

    opening_stats = boxes_1[1].select("div.stats-row")
    kills = opening_stats[0].select("span")[1].text
    deaths = opening_stats[1].select("span")[1].text
    kd = opening_stats[2].select("span")[1].text
    kill_rating = opening_stats[3].select("span")[1].text
    win_percent_after_first_kill = (
        opening_stats[4].select("span")[1].text.replace("%", "")
    )
    first_kill_in_won_rounds = opening_stats[5].select("span")[1].text.replace("%", "")

    opening = {
        "kills": kills,
        "deaths": deaths,
        "kd": kd,
        "kill_rating": kill_rating,
        "win_percent_after_first_kill": win_percent_after_first_kill,
        "first_kill_in_won_rounds": first_kill_in_won_rounds,
    }

    round_stats = boxes_2[0].select("div.stats-row")
    kill_0 = round_stats[0].select("span")[1].text
    kill_1 = round_stats[1].select("span")[1].text
    kill_2 = round_stats[2].select("span")[1].text
    kill_3 = round_stats[3].select("span")[1].text
    kill_4 = round_stats[4].select("span")[1].text
    kill_5 = round_stats[5].select("span")[1].text

    rounds = {
        "0_kill": kill_0,
        "1_kill": kill_1,
        "2_kill": kill_2,
        "3_kill": kill_3,
        "4_kill": kill_4,
        "5_kill": kill_5,
    }

    weapon_stats = boxes_2[1].select("div.stats-row")
    rifle = weapon_stats[0].select("span")[1].text
    sniper = weapon_stats[1].select("span")[1].text
    smg = weapon_stats[2].select("span")[1].text
    pistol = weapon_stats[3].select("span")[1].text
    grenade = weapon_stats[4].select("span")[1].text
    other = weapon_stats[5].select("span")[1].text

    weapon_kills = {
        "rifle": rifle,
        "sniper": sniper,
        "smg": smg,
        "pistol": pistol,
        "grenade": grenade,
        "other": other,
    }

    return opening, rounds, weapon_kills


def get_side_stats(soup, side):

    stats_container = soup.select_one("div.role-stats-container")
    if side == "ct":
        div_class = "stats-side-ct"
    elif side == "t":
        div_class = "stats-side-t"

    # Firepower:
    container = stats_container.select_one("div.role-firepower")
    overall_container = container.select_one(f"div.{div_class}")
    f_overall = overall_container.select_one("div.row-stats-section-score").text.split(
        "/"
    )[0]

    # Stats are not in order as in dictionary, hltv html is left->right->left->right and not from top to bottom and next column
    stats = container.select(f"div.role-stats-row.{div_class}")
    f_kpr = stats[0].select_one("div.role-stats-data").text
    f_rounds_with_kill_pct = (
        stats[1].select_one("div.role-stats-data").text.replace("%", "")
    )
    f_kpr_win = stats[2].select_one("div.role-stats-data").text
    f_rating = stats[3].select_one("div.role-stats-data").text
    f_adr = stats[4].select_one("div.role-stats-data").text
    f_rounds_with_multikill_pct = (
        stats[5].select_one("div.role-stats-data").text.replace("%", "")
    )
    f_adr_win = stats[6].select_one("div.role-stats-data").text
    f_pistol_rating = stats[7].select_one("div.role-stats-data").text

    firepower = {
        "overall": f_overall,  # Based on kills, damage, and multi-kills - raw fragging power rating/100
        "kills_per_round": f_kpr,
        "kills_per_round_win": f_kpr_win,  # KPR in won rounds only
        "damage_per_round": f_adr,
        "damage_per_round_win": f_adr_win,  # ADR in won rounds only
        "rounds_with_kill_pct": f_rounds_with_kill_pct,  # Percentage of rounds where player got at least one kill
        "rating_2_1": f_rating,  # HLTV Rating 2.1
        "multi_kill_rounds_pct": f_rounds_with_multikill_pct,  # Percentage of rounds with 2+ kills
        "pistol_round_rating": f_pistol_rating,  # Rating 2.1 in pistol rounds only
    }

    # Entrying:
    container = stats_container.select_one("div.role-entrying")
    overall_container = container.select_one(f"div.{div_class}")
    e_overall = overall_container.select_one("div.row-stats-section-score").text.split(
        "/"
    )[0]

    stats = container.select(f"div.role-stats-row.{div_class}")
    e_sbt_pr = stats[0].select_one("div.role-stats-data").text
    e_td_pr = stats[1].select_one("div.role-stats-data").text
    e_td_pct = stats[2].select_one("div.role-stats-data").text.replace("%", "")
    e_odt_pct = stats[3].select_one("div.role-stats-data").text.replace("%", "")
    e_apr = stats[4].select_one("div.role-stats-data").text
    e_sr_pct = stats[5].select_one("div.role-stats-data").text.replace("%", "")

    entrying = {
        "overall": e_overall,  # Based on traded deaths (% and per round) and saves by teammates rating/100
        "saved_by_teammate_per_round": e_sbt_pr,  # How often teammates save this player per round
        "traded_deaths_per_round": e_td_pr,  # Deaths that get traded by teammates per round
        "traded_deaths_pct": e_td_pct,  # Percentage of deaths that get traded
        "opening_deaths_traded_pct": e_odt_pct,  # Percentage of opening deaths that get traded
        "assists_per_round": e_apr,
        "support_rounds_pct": e_sr_pct,  # Percentage of rounds where player provided support
    }

    # Trading:
    container = stats_container.select_one("div.role-trading")
    overall_container = container.select_one(f"div.{div_class}")
    t_overall = overall_container.select_one("div.row-stats-section-score").text.split(
        "/"
    )[0]

    stats = container.select(f"div.role-stats-row.{div_class}")
    t_st_pr = stats[0].select_one("div.role-stats-data").text
    t_tk_pr = stats[1].select_one("div.role-stats-data").text
    t_tk_pct = stats[2].select_one("div.role-stats-data").text.replace("%", "")
    t_ak_pct = stats[3].select_one("div.role-stats-data").text.replace("%", "")
    t_dpk = stats[4].select_one("div.role-stats-data").text

    trading = {
        "overall": t_overall,  # Based on trade kills (% and per round) and teammate saves rating/100
        "saved_teammate_per_round": t_st_pr,  # How often this player saves teammates per round
        "trade_kills_per_round": t_tk_pr,  # Kills that trade teammate deaths per round
        "trade_kills_pct": t_tk_pct,  # Percentage of kills that are trades
        "assisted_kills_pct": t_ak_pct,  # Percentage of kills where player got assist
        "damage_per_kill": t_dpk,  # Average damage dealt per kill
    }

    # Opening:
    container = stats_container.select_one("div.role-opening")
    overall_container = container.select_one(f"div.{div_class}")
    o_overall = overall_container.select_one("div.row-stats-section-score").text.split(
        "/"
    )[0]

    stats = container.select(f"div.role-stats-row.{div_class}")
    o_ok_pr = stats[0].select_one("div.role-stats-data").text
    o_od_pr = stats[1].select_one("div.role-stats-data").text
    o_oa_pct = stats[2].select_one("div.role-stats-data").text.replace("%", "")
    o_os_pct = stats[3].select_one("div.role-stats-data").text.replace("%", "")
    o_w_pct_aok = stats[4].select_one("div.role-stats-data").text.replace("%", "")
    o_apr = stats[5].select_one("div.role-stats-data").text

    opening = {
        "overall": o_overall,  # Based on opening kills per round and opening attempts rating/100
        "opening_kills_per_round": o_ok_pr,  # First kills of the round per round
        "opening_deaths_per_round": o_od_pr,  # First deaths of the round per round
        "opening_attempts_pct": o_oa_pct,  # Percentage of rounds where player attempts opening duel
        "opening_success_pct": o_os_pct,  # Success rate in opening duels
        "win_pct_after_opening_kill": o_w_pct_aok,  # Team win rate after this player gets opening kill
        "attacks_per_round": o_apr,  # Aggressive actions per round
    }

    # Clutching:
    container = stats_container.select_one("div.role-clutching")
    overall_container = container.select_one(f"div.{div_class}")
    c_overall = overall_container.select_one("div.row-stats-section-score").text.split(
        "/"
    )[0]

    stats = container.select(f"div.role-stats-row.{div_class}")
    c_ppr = stats[0].select_one("div.role-stats-data").text
    c_la_pct = stats[1].select_one("div.role-stats-data").text.replace("%", "")
    c_1v1_win_pct = stats[2].select_one("div.role-stats-data").text.replace("%", "")
    c_ta_pr_s = stats[3].select_one("div.role-stats-data").text

    # turn it into seconds without ending "1m 4s" -> "64"
    m = re.search(r"(\d+)\s*m", c_ta_pr_s)
    s_ = re.search(r"(\d+)\s*s", c_ta_pr_s)
    if m:
        minutes = int(m.group(1))
    if s_:
        seconds = int(s_.group(1))
    c_ta_pr_s = minutes * 60 + seconds

    c_spr_loss_pct = stats[4].select_one("div.role-stats-data").text.replace("%", "")

    clutching = {
        "overall": c_overall,  # Based on clutches won and time alive per round rating/100
        "clutch_points_per_round": c_ppr,  # Clutch situation points per round
        "last_alive_pct": c_la_pct,  # Percentage of rounds where player is last alive
        "one_vs_one_win_pct": c_1v1_win_pct,  # Win rate in 1v1 situations
        "time_alive_per_round_seconds": c_ta_pr_s,  # Average survival time per round in seconds
        "saves_per_round_loss_pct": c_spr_loss_pct,  # Percentage of lost rounds where player saved
    }

    # Sniping:
    container = stats_container.select_one("div.role-sniping")
    overall_container = container.select_one(f"div.{div_class}")
    s_overall = overall_container.select_one("div.row-stats-section-score").text.split(
        "/"
    )[0]

    stats = container.select(f"div.role-stats-row.{div_class}")
    s_kpr = stats[0].select_one("div.role-stats-data").text
    s_sk_pct = stats[1].select_one("div.role-stats-data").text.replace("%", "")
    s_rw_sk_pct = stats[2].select_one("div.role-stats-data").text.replace("%", "")
    s_rw_smk_pct = stats[3].select_one("div.role-stats-data").text.replace("%", "")
    s_ok_pr = stats[4].select_one("div.role-stats-data").text

    sniping = {
        "overall": s_overall,  # Based on AWP/SSG kills and multi-kills rating/100
        "sniper_kills_per_round": s_kpr,  # AWP/SSG kills per round
        "sniper_kills_pct": s_sk_pct,  # Percentage of kills with AWP/SSG
        "rounds_with_sniper_kills_pct": s_rw_sk_pct,  # Percentage of rounds with AWP/SSG kill
        "sniper_multi_kill_rounds": s_rw_smk_pct,  # Rounds with 2+ AWP/SSG kills per round
        "sniper_opening_kills_per_round": s_ok_pr,  # Opening kills with AWP/SSG per round
    }

    # Utility:
    container = stats_container.select_one("div.role-utility")
    overall_container = container.select_one(f"div.{div_class}")
    u_overall = overall_container.select_one("div.row-stats-section-score").text.split(
        "/"
    )[0]

    stats = container.select(f"div.role-stats-row.{div_class}")
    u_dpr = stats[0].select_one("div.role-stats-data").text
    u_uk_p100r = stats[1].select_one("div.role-stats-data").text
    u_ft_pr = stats[2].select_one("div.role-stats-data").text
    u_fa_pr = stats[3].select_one("div.role-stats-data").text
    u_tof_pr = stats[4].select_one("div.role-stats-data").text

    utility = {
        "overall": u_overall,  # Based on flashbang stats and grenade damage per round rating/100
        "utility_damage_per_round": u_dpr,  # HE/Molotov/Incendiary damage per round
        "utility_kills_per_100_rounds": u_uk_p100r,  # Grenade kills per 100 rounds
        "flashes_thrown_per_round": u_ft_pr,  # Flashbangs thrown per round
        "flash_assists_per_round": u_fa_pr,  # Assists from flashbangs per round
        "time_opponent_flashed_per_round": u_tof_pr,  # Seconds enemies blinded per round
    }

    return firepower, entrying, trading, opening, clutching, sniping, utility


async def scrape_player(session_id, headless, url_list):
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

                stats_url = update_player_url(url)
                individual_url = stats_url.replace("players/", "players/individual/")

                # Get HTML
                await page.goto(stats_url)
                html = await page.inner_html("div.stats-player")
                soup = BeautifulSoup(html, "html.parser")

                name = (
                    soup.select_one("h1.summaryNickname").text.strip().replace(" ", "")
                )
                country = soup.select_one("img.flag").get("title")
                team = (
                    soup.select_one("div.SummaryTeamname a")
                    .text.strip()
                    .replace(" ", "")
                )
                age = soup.select_one("div.summaryPlayerAge").text.split(" ")[0]

                overall = get_overall_stats(soup)

                opening, rounds, weapon_kills = await get_individual_stats(
                    page, individual_url
                )

                (
                    ct_firepower,
                    ct_entrying,
                    ct_trading,
                    ct_opening,
                    ct_clutching,
                    ct_sniping,
                    ct_utility,
                ) = get_side_stats(soup, "ct")

                (
                    t_firepower,
                    t_entrying,
                    t_trading,
                    t_opening,
                    t_clutching,
                    t_sniping,
                    t_utility,
                ) = get_side_stats(soup, "t")

                player_info = {
                    "name": name,
                    "country": country,
                    "team": team,
                    "age": age,
                    "overall": overall,
                    "opening": opening,
                    "round": rounds,
                    "weapon": weapon_kills,
                    "ct-side": {
                        "firepower": ct_firepower,
                        "entrying": ct_entrying,
                        "trading": ct_trading,
                        "opening": ct_opening,
                        "clutching": ct_clutching,
                        "sniping": ct_sniping,
                        "utility": ct_utility,
                    },
                    "t-side": {
                        "firepower": t_firepower,
                        "entrying": t_entrying,
                        "trading": t_trading,
                        "opening": t_opening,
                        "clutching": t_clutching,
                        "sniping": t_sniping,
                        "utility": t_utility,
                    },
                }

                # thread-safe
                async with lock:
                    if player_info not in player_data:
                        player_data.append(player_info)

                end_time = time.perf_counter()
                elapsed = end_time - start_time

                if config["team_amount"] == -1:
                    status(
                        f"[+] [Session {session_id}] Successfully scraped {name} ({len(player_data)} / {len(df['player_urls']) * 5}) ({elapsed:.2f}s)",
                        bcolors.SUCCESS,
                    )
                else:
                    status(
                        f"[+] [Session {session_id}] Successfully scraped {name} ({len(player_data)} / {config["team_amount"] * 5}) ({elapsed:.2f}s)",
                        bcolors.SUCCESS,
                    )

                if type(config["session_timeout"]) == list:
                    await asyncio.sleep(
                        random.uniform(
                            config["session_timeout"][0],
                            config["session_timeout"][1],
                        )
                    )
                else:
                    await asyncio.sleep(config["session_timeout"])

            except Exception as e:
                status(
                    f"[-] Session {session_id}: Exception - {e}",
                    bcolors.FAIL,
                )
                break


def distribute_urls(
    df, team_amount=config["team_amount"], session_amount=config["session_amount"]
):
    # Create a list of empty lists for each session
    url_lists = [[] for _ in range(session_amount)]

    # Get all URLs
    urls = []
    url_str_list = df["player_urls"].tolist()
    for url_list_str in url_str_list:
        # pandas saves the player_url list as a string, need to make it a list again before looping
        url_list = ast.literal_eval(url_list_str)
        for url in url_list:
            urls.append(url)

    # Distribute the URLs evenly across the sessions
    for url in urls[: team_amount * 5]:
        smallest_list = min(url_lists, key=len)
        smallest_list.append(url)

    return url_lists


async def main():
    total_start_time = time.perf_counter()

    if config["team_amount"] == -1:
        status(
            f"[!] Scraping all players from {len(df)} teams",
            bcolors.WARNING,
        )
    else:
        status(
            f"[!] Scraping all players from {config['team_amount']} teams",
            bcolors.WARNING,
        )

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
                scrape_player(
                    session_id=i,
                    headless=is_headless,
                    url_list=urls_per_session[i],
                )
            )
        )

    await asyncio.gather(*tasks)

    total_elapsed = time.perf_counter() - total_start_time

    final_df = pd.DataFrame(player_data)
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
