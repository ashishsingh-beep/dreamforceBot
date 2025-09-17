from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import random
import logging
from typing import List, Dict
import pandas as pd
from fake_useragent import UserAgent
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import random, string
import json
import threading
# Removed signal and atexit imports for Streamlit compatibility

# Set up supabase 
load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_driver(driver):
    """Cleanup function for driver"""
    if driver:
        try:
            driver.quit()
            logger.info("Browser closed")
        except:
            pass

def setup_driver():
    """Setup Chrome driver with anti-detection options"""
    chrome_options = Options()
    
    # Anti-detection measures
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def human_like_delay(min_delay=3, max_delay=8, extra_delay=0):
    """Add random delay to simulate human behavior"""
    delay = random.uniform(min_delay + extra_delay, max_delay + extra_delay)
    logger.info(f"Waiting {delay:.2f} seconds...")
    time.sleep(delay)

def exponential_backoff(attempt):
    """Exponential backoff for retries"""
    delay = min(300, (2 ** attempt) + random.uniform(0, 1))
    logger.info(f"Backoff delay: {delay:.2f} seconds")
    time.sleep(delay)

def check_rate_limit(session_requests):
    """Check if we need to take a longer break"""
    # Long break every 10 requests
    if session_requests % 10 == 0:
        long_delay = random.uniform(60, 120)
        logger.info(f"Taking extended break: {long_delay:.2f} seconds")
        time.sleep(long_delay)
    
    return session_requests + 1

def restart_session(driver):
    """Restart the browser session"""
    if driver:
        driver.quit()
        time.sleep(random.uniform(5, 15))
    driver = setup_driver()
    return driver

def perform_login(driver, username=None, password=None):
    """Handle login process"""
    wait = WebDriverWait(driver, 10)
    
    # Login page with human-like delay
    driver.get("https://www.linkedin.com/login")
    time.sleep(random.uniform(2, 4))

    if username and password:
        logged_in = False

        # Only login with credentials, no cookie logic
        logger.info("Logging in with credentials...")
        if "login" not in driver.current_url.lower():
            driver.get("https://www.linkedin.com/login")
            time.sleep(random.uniform(2, 4))
        
        user_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
        pass_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
        user_input.clear()
        
        # Type slowly like human
        for char in username:
            user_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
            
        pass_input.clear()
        time.sleep(random.uniform(0.5, 1.0))
        
        for char in password:
            pass_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

        sign_in_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        time.sleep(random.uniform(1, 2))
        sign_in_btn.click()
        
        time.sleep(random.uniform(3, 5))
        
        if "feed" in driver.current_url.lower() or "home" in driver.current_url.lower():
            logger.info("Login successful!")
            logged_in = True
    else:
        # Manual login
        print("Please log in to LinkedIn manually...")
        try:
            WebDriverWait(driver, 300).until(lambda d: "feed" in d.current_url.lower())
            print("Login successful! Proceeding with scraping...")
        except:
            print("Login failed or took too long.")
            return False

    time.sleep(random.uniform(2, 4))

    # Handle security checkpoint
    if "checkpoint" in driver.current_url.lower():
        input("Complete the security check in the browser and press Enter here...")
        time.sleep(5)
    
    return True

def scrape_profile(driver, url, wait):
    """Scrape a single LinkedIn profile"""
    # ORIGINAL XPaths - UNCHANGED
    xpath_name = "//h1[contains(@class, 't-24')]"
    xpath_bio = '//*[@id="profile-content"]/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[1]/div[2]'
    xpath_skills = "//section[descendant::div[@id='skills']]/div[3]/ul/li//a[contains(@href, 'SKILL')]"
    xpath_exp = "(//section[.//*[@id='experience']]//ul[1]/li)[1]"
    xpath_about = "//section[descendant::div[@id='about']]/div[3]"
    xpath_company_lkd = "//section[.//*[@id='experience']]//ul[1]//a[@data-field='experience_company_logo']"
    xpath_title = "(((//section[.//div[@id='experience']]//li)[1]//a)[2]/div)[1]"
    xpath_company_name = "(//section[.//*[@id='experience']]//ul[1]//a[@data-field='experience_company_logo'])[2]/span[1]/span[@aria-hidden='true']"
    xpath_location = "//div[*/a[contains(@href,'contact-info')]]/span[1]"
    
    details = {
        'lead_id': None,
        'name': None,
        'title': None,
        'location': None,
        'profile_url': url,
        'bio': None,
        'skills': [],
        'experience': None,
        'company_name': None,
        'company_page_url': None,
    }

    try:
        driver.get(url)
        time.sleep(random.uniform(3, 6))

        # Simulate human scrolling
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(random.uniform(1, 2))

        # Lead_id 
        try:
            if '/in/' in url:
                lead_arr = url.split('/')
                idx = lead_arr.index('in')
                lead_id = lead_arr[idx+1]
                if '?' in lead_id:
                    lead_id = lead_id.split('?')[0]
                details['lead_id'] = lead_id
        except:
            details['lead_id'] = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

        # Name - ORIGINAL LOGIC PRESERVED
        name_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath_name)))
        details['name'] = name_element.text.strip()

        # Bio - ORIGINAL LOGIC PRESERVED
        try:
            bio_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath_bio)))
            details['bio'] = bio_element.text.strip()
        except:
            details['bio'] = ""

        # Title - ORIGINAL LOGIC PRESERVED
        try:
            title_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath_title)))
            details['title'] = title_element.text.strip()
        except:
            details['title'] = ""

        # Location - ORIGINAL LOGIC PRESERVED
        try:
            location_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath_location)))
            details['location'] = location_element.text.strip()
        except:
            details['location'] = None

        # Company Name - ORIGINAL LOGIC PRESERVED
        try:
            company_name_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath_company_name)))
            details['company_name'] = company_name_element.text.strip()
        except:
            details['company_name'] = None

        # About - ORIGINAL LOGIC PRESERVED
        try:
            about_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath_about)))
            details['bio'] += "\n" + about_element.text.strip()
        except:
            pass

        # Scroll more for additional content
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(random.uniform(1, 2))

        # Skills - ORIGINAL LOGIC PRESERVED
        try:
            skills_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath_skills)))
            details['skills'] = [skill.text.strip() for skill in skills_elements]
        except:
            details['skills'] = []

        # Experience - ORIGINAL LOGIC PRESERVED
        try:
            exp_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath_exp)))
            details['experience'] = "\n".join([x.text.strip() for x in exp_elements])
        except:
            details['experience'] = ""

        # Company LinkedIn page - ORIGINAL LOGIC PRESERVED
        try:
            comp_ldk_pages = wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath_company_lkd)))
            company_links = [comp.get_attribute('href') for comp in comp_ldk_pages if comp.get_attribute('href')]
            details['company_page_url'] = company_links[0] if company_links else None
        except:
            details['company_page_url'] = None

        return details if details['name'] else None

    except Exception as e:
        logger.error(f"Error processing profile {url}: {str(e)}")
        return None

def get_linkedin_profile_details(urls: List[str], username: str = None, password: str = None, 
                               resume_from_checkpoint: bool = True, progress_callback=None, 
                               status_callback=None) -> List[Dict]:
    """
    Streamlit-compatible LinkedIn scraper without signal handlers
    
    Args:
        progress_callback: Function to call with progress updates
        status_callback: Function to call with status updates
    """
    
    scraped_data = []
    current_index = 0
    
    # Setup driver
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    session_requests = 0
    max_session_requests = 50

    try:
        # Perform login
        if status_callback:
            status_callback("🔑 Logging into LinkedIn...")
            
        if not perform_login(driver, username, password):
            logger.error("Login failed")
            if status_callback:
                status_callback("❌ Login failed")
            return scraped_data

        if status_callback:
            status_callback("✅ Login successful! Starting to scrape profiles...")

        # Process URLs starting from current_index
        for i in range(current_index, len(urls)):
            url = urls[i]
            logger.info(f"Processing profile {i+1}/{len(urls)}: {url}")
            
            if status_callback:
                status_callback(f"🔍 Processing profile {i+1}/{len(urls)}")
            
            # Rate limiting check
            session_requests = check_rate_limit(session_requests)
            
            # Restart session if needed
            if session_requests >= max_session_requests:
                logger.info("Restarting session to avoid detection")
                if status_callback:
                    status_callback("🔄 Restarting browser session...")
                driver = restart_session(driver)
                wait = WebDriverWait(driver, 10)
                session_requests = 0
                # Re-login after restart
                if not perform_login(driver, username, password):
                    logger.error("Re-login failed after session restart")
                    if status_callback:
                        status_callback("❌ Re-login failed after session restart")
                    break

            # Scrape profile
            try:
                profile_data = scrape_profile(driver, url, wait)
                
                if profile_data:
                    scraped_data.append(profile_data)
                    logger.info(f"Successfully scraped: {profile_data['name']}")
                    
                    # Save progress every 5 profiles
                    if len(scraped_data) % 5 == 0:
                        save_progress(scraped_data, i + 1, urls, progress_callback)

            except Exception as e:
                logger.error(f"Error processing profile {url}: {str(e)}")
                if status_callback:
                    status_callback(f"⚠️ Error processing profile: {str(e)[:100]}...")
                if i < len(urls) - 1:
                    exponential_backoff(1)
                continue
            
            # Update current index
            current_index = i + 1
            
            # Update progress
            if progress_callback:
                progress_callback({
                    'scraped_count': len(scraped_data),
                    'current_index': current_index,
                    'total_urls': len(urls),
                    'progress_percent': (current_index / len(urls)) * 100
                })
            
            # Human-like delay between profiles
            if i < len(urls) - 1:
                human_like_delay(4, 8, random.uniform(2, 5))

        if status_callback:
            status_callback(f"🎉 Scraping completed! Total profiles: {len(scraped_data)}")

        return scraped_data

    except Exception as e:
        logger.error(f"Error in get_linkedin_profile_details: {str(e)}")
        if status_callback:
            status_callback(f"❌ Error: {str(e)}")
        return scraped_data
    finally:
        cleanup_driver(driver)
