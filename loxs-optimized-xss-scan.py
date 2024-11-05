#!/usr/bin/python3

import os
import time
import logging
import asyncio
from urllib.parse import urlsplit, parse_qs, urlencode, urlunsplit
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from colorama import Fore
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Initialize logging and warnings
logging.getLogger('WDM').setLevel(logging.ERROR)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_payloads(filepath="payloads/xss.txt"):
    try:
        with open(filepath, "r") as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(Fore.RED + f"[!] Error loading payloads: {e}")
        exit(1)

def load_urls(filepath="xssurl.txt"):
    try:
        with open(filepath, "r") as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(Fore.RED + f"[!] Error loading URLs: {e}")
        exit(1)

def generate_payload_urls(url, payload):
    url_combinations = []
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    scheme = scheme or 'http'
    query_params = parse_qs(query_string, keep_blank_values=True)
    for key in query_params:
        modified_params = query_params.copy()
        modified_params[key] = [payload]
        modified_query_string = urlencode(modified_params, doseq=True)
        modified_url = urlunsplit((scheme, netloc, path, modified_query_string, fragment))
        url_combinations.append(modified_url)
    return url_combinations

async def check_vulnerability(driver, url, payloads, vulnerable_urls, total_scanned, total_tasks):
    for payload in payloads:
        payload_urls = generate_payload_urls(url, payload)
        for payload_url in payload_urls:
            try:
                driver.get(payload_url)
                total_scanned[0] += 1
                current_progress = (total_scanned[0] / total_tasks) * 100
                print_progress(current_progress, total_scanned[0], total_tasks)

                try:
                    WebDriverWait(driver, 0.5).until(EC.alert_is_present())
                    alert = driver.switch_to.alert
                    print(Fore.GREEN + f"[✓] Vulnerable: {payload_url} - Alert Text: {alert.text}")
                    vulnerable_urls.add(payload_url)
                    alert.accept()
                except TimeoutException:
                    pass
            except UnexpectedAlertPresentException:
                print(Fore.CYAN + f"[!] Unexpected Alert: {payload_url} - Might be Vulnerable!")
                vulnerable_urls.add(payload_url)
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                except:
                    pass

async def scan(urls, payloads, concurrency):
    total_scanned = [0]
    vulnerable_urls = set()
    total_tasks = len(urls) * len(payloads)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)

    driver_service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=driver_service, options=chrome_options)

    try:
        tasks = []
        semaphore = asyncio.Semaphore(concurrency)

        for url in urls:
            task = asyncio.create_task(bound_check_vulnerability(driver, url, semaphore, payloads, vulnerable_urls, total_scanned, total_tasks))
            tasks.append(task)

        await asyncio.gather(*tasks)
    finally:
        driver.quit()
    
    return vulnerable_urls

async def bound_check_vulnerability(driver, url, semaphore, payloads, vulnerable_urls, total_scanned, total_tasks):
    async with semaphore:
        await check_vulnerability(driver, url, payloads, vulnerable_urls, total_scanned, total_tasks)

def print_progress(percentage, scanned, total):
    print(Fore.YELLOW + f"\rProgress: [{scanned}/{total}] ({percentage:.2f}%)", end="")

def print_scan_summary(total_found, total_scanned, start_time, end_time):
    time_taken = int(end_time - start_time)
    summary = (
        f"{Fore.YELLOW}\n→ Scanning finished.\n"
        f"• Total found: {Fore.GREEN}{total_found}{Fore.YELLOW}\n"
        f"• Total scanned: {total_scanned}\n"
        f"• Time taken: {time_taken} seconds{Fore.RESET}"
    )
    print(summary)

def run_scan(concurrency=30):
    payloads = load_payloads()
    urls = load_urls()
    start_time = time.time()

    vulnerable_urls = asyncio.run(scan(urls, payloads, concurrency))

    end_time = time.time()
    print_scan_summary(len(vulnerable_urls), len(urls) * len(payloads), start_time, end_time)

if __name__ == "__main__":
    print(Fore.GREEN + "Starting XSS scanner...\n")
    run_scan()
