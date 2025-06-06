# python-hltv-scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A simple and open-source HLTV.org web scraper built with Camoufox and BeautifulSoup, written entirely in Python.

## This will get a major update/overhaul very soon, you can expect:
- Every script will be fully asynchronous! This means you can scrape data in multiple parallel sessions, drastically improving speed and efficiency.
- Integrated proxy support with automatic rotation to help you stay under the radar and avoid IP bans.
- Enhanced security measures including dynamic User-Agent rotation, cookie management, and support for auto-login to seamlessly bypass Cloudflare and other anti-bot protections.
- Cleaner, modular codebase designed for easy customization and extension — perfect for both beginners and advanced users.
- Improved error handling and retry logic to make the scraping process more robust and reliable.
- Detailed logging and progress reporting so you always know what’s happening.
- Ongoing active maintenance and improvements based on your feedback.
- An improved README.md to help you guys understand my mess.

## And the best out of all... Player Data Scraping! 🎉
Stay tuned... ;)

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Contact](#contact)

---

## Features

- 🔎 Scrape match and team data directly from HLTV.org
- 🚀 Fast and lightweight, with minimal dependencies
- 🧩 Written in pure Python, using Camoufox and BeautifulSoup
- 📝 Easy to understand code
- 💡 Open source and actively maintained

---

## Installation

Install via git & pip:

```bash
git clone https://github.com/ClassicalClemi/python-hltv-scraper.git
cd python-hltv-scraper
pip install -r requirements.txt
```

Python 3.x is needed.

To install the camoufox browser:

```bash
camoufox fetch
```

---

## Usage

You can edit the configuration of every file in the file itself.
After you've made your changes/configuration, just run the file and wait for the output to say that it finished.

You can start a script via console like this:

```bash
python get_team_data_new.py
```

You should configure it before running.

Before scraping team or match data you need to run the team or match URL file. This will scrape the URLs from HLTV.org for the other files to use it. The saved data will automatically be saved in data/name.csv by default. You can easily change this in the config of each file. 

---

## Configuration

There is a config dictionary in every file.
You can change stuff like file to read, savefile, amount and so on.
Every option is commented so you know what it does.

---

## Contact

You can contact me on Discord: **clxmi**

Again, this is my first project ever. There will be many problems, please be kind :)
