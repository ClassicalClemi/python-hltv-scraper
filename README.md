# python-hltv-scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A simple and open-source HLTV.org web scraper built with AsyncCamoufox and BeautifulSoup, written entirely in Python.

---

## Table of Contents

- [Overview](#overview)  
- [Features](#features)  
- [Installation](#installation)  
- [Usage](#usage)  
- [Project Structure](#project-structure)  
- [Configuration](#configuration)  
- [Advanced Configuration](#advanced-configuration)  
  - [Proxies](#proxies)  
  - [User Agents](#user-agents)  
  - [Cookies & Sessions](#cookies--sessions)  
- [Contributing](#contributing)  
- [Contact](#contact)  

---

## Overview

This project provides a fast, asynchronous, and secure web scraper for HLTV.org, designed to overcome Cloudflare protections using Camoufox, asyncio, BeautifulSoup, and pandas. It supports scraping of recent matches, teams, players, and detailed match data. This is also my first project ever! I would be honored if you could leave feedback and maybe also a star :)

---

## Features

- Fully asynchronous scraping for high speed and efficiency  
- Cloudflare bypass using Camoufox with TLS/JA3 fingerprinting  
- Proxy support with automatic rotation (optional)  
- Dynamic User-Agent rotation for stealth  
- Cookie and session management for persistent scraping  
- Modular scripts for scraping matches, teams, and players  
- Data saved in CSV format for easy analysis  
- Detailed logging and progress reporting  

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/ClassicalClemi/python-hltv-scraper.git
cd python-hltv-scraper
pip install -r requirements.txt
```

Make sure you have Python 3.x installed.

Install the Camoufox browser:

```bash
camoufox fetch
```

---

## Usage

Each script can be configured via a `config` dictionary inside the file. Configure input/output files, scraping limits, and other options before running.

Run a script from the command line:

```bash
python async_get_team_data.py
```

**Important:** Before scraping detailed team or match data, run the corresponding URL scraper scripts (`async_get_team_urls.py`, `async_get_recent_match_urls.py`) to collect URLs.

Scraped data is saved by default in the `data/` folder as CSV files. You can change paths in the config.

---

## Project Structure

- `async_get_recent_match_urls.py` — Scrapes recent matches from `https://www.hltv.org/results`
- `async_get_match_data.py` — Scrapes in-depth data from scraped match URLs
    <details> 
      <summary>Exact structure:</summary>
      
      match_info = {
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
      "maps": [
                    {"map": "Dust2", "picked_by": "team_1", "winner": "team_1", "score": "16-14"},
                    {"map": "Mirage", "picked_by": "team_2", "winner": "team_2", "score": "16-12"},
                    {"map": "Inferno", "picked_by": "random", "winner": "team_1", "score": "16-10"}
                ]
    </details>
- `async_get_team_urls.py` — Scrapes all team URLs from `https://www.hltv.org/ranking/teams`
- `async_get_team_data.py` — Scrapes in-depth data from scraped team URLs
      <details> 
      <summary>Exact structure:</summary>

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
    </details>
- `async_get_player_data.py` — Scrapes in-depth data of every player in every scraped team
      <details> 
      <summary>Exact structure:</summary>

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
    </details>

---

## Configuration

Each script contains a `config` dictionary with options such as:

- `file_to_read` — str — CSV file location to read URLs from
- `savefile_location` — str — CSV file location to save scraped data
- `???_amount` — int — Amount of items to scrape
- `headless` — bool — Hide/Show the browser/s while scraping
- `screen` — Screen — Min/max screen width/height
- `screen_amount` — int — Amount of browsers you want to show (if headless = False)
- `session_amount` — int — Amount of parallel sessions (you will get rate limited if you set this too high)
- `session_timeout` — int/list — Timeout afer session in seconds, random range possible: [0.8, 1.2]
- `use_proxy` — bool — Use proxies
- `use_proxy_once` — bool — Each proxy only gets used by one session
- `proxy_location` — str — TXT file location to read proxies, (format: server:port:username:password), 1 every line
- `user_agents_location` — str — JSON file location to read user_agents
- `cookie_location` — str — JSON file location to get cookies to apply

  <details> 
      <summary>Example structure:</summary>
      
      config = {
            "file_to_read": "rework/data/team_urls.csv",
            "savefile_location": "rework/data/team_data.csv",
            "team_amount": 100,  # -1 = all
            "headless": True,
            "screen": Screen(max_width=1920, max_height=1080),
            "screen_amount": 1,
            "session_amount": 5,
            "session_timeout": 1,
            "use_proxy": True,
            "use_proxy_once": True,
            "proxy_location": "rework/data/proxies.txt",
            "user_agents_location": "rework/data/user_agents.json",
            "cookie_location": "rework/data/autologin_cookie.json",
        }
    </details>

All options are also commented inside the scripts for clarity.

---

## Advanced Configuration

### Proxies

To avoid IP bans and improve anonymity, you can configure proxy support:

- Proxies (as .txt file):
  
  ![image](https://github.com/user-attachments/assets/ca43d659-4272-4300-965b-2dbc26c7d0fe)

### User Agents

Dynamic User-Agent rotation helps mimic real browsers:

- User Agents (as .json file):
  
  ![image](https://github.com/user-attachments/assets/e7b86a97-5821-46dc-aa8f-568b3302e406)

### Cookies & Sessions

Persistent cookies and session management improve Cloudflare bypass:

- Cookies incl. autologin (as .json file):
  
  ![image](https://github.com/user-attachments/assets/953a6a4d-9bb6-46ec-b3e5-5243ddb93423)

How to get autologin cookie:
- Open HLTV.org
- Login
- Inspect the site (F12)
- Click on the "Application" tab
- At Cookies click/open "https://www.hltv.org"
- There is a table with all your cookies, including "autologin"

---

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open issues or pull requests on GitHub.

---

## Contact

You can contact me on Discord: **clxmi**

---
