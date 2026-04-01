@echo off
REM DTFBL OnRoto Daily Scraper
REM This file is called by Windows Task Scheduler at 11pm nightly.
REM It wakes WSL2 and runs the Python scraper.

wsl -e bash -c "cd /home/flaco/dev/fb_auction/dtfbl-draft-analysis && python3 onroto_scraper.py"
