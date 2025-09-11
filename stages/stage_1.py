import os
import time
import random
import logging
import json
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
import pandas as pd
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up supabase 
load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)


def slow_type(element, text, delay_range=(0.05, 0.15)):
    """Simulate human-like typing with random delays between keystrokes"""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(*delay_range))


def save_cookies_to_cache(driver, expiry_hours=24):
    """Save browser cookies to JSON file with expiry date"""
    try:
        cookies = driver.get_cookies()
        cache_data = {
            "cookies": cookies,
            "expiry": (datetime.now() + timedelta(hours=expiry_hours)).isoformat(),
            "created": datetime.now().isoformat()
        }
        
        with open('cookie.json', 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Cookies saved to cache with {expiry_hours}h expiry")
        return True
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")
        return False


def load_cookies_from_cache():
    """Load cookies from JSON file if not expired"""
    try:
        if not os.path.exists('cookie.json'):
            logger.info("No cookie cache file found")
            return None
            
        with open('cookie.json', 'r') as f:
            cache_data = json.load(f)
        
        expiry = datetime.fromisoformat(cache_data["expiry"])
        
        if datetime.now() > expiry:
            logger.info("Cookie cache has expired")
            return None
        
        logger.info("Valid cookie cache found")
        return cache_data["cookies"]
        
    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
        return None


def apply_cookies_to_driver(driver, cookies):
    """Apply saved cookies to the current driver session"""
    try:
        # Navigate to LinkedIn first to set the domain
        driver.get("https://www.linkedin.com")
        time.sleep(random.uniform(2, 4))
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"Failed to add cookie {cookie.get('name', 'unknown')}: {e}")
        
        logger.info("Cookies applied to driver")
        return True
    except Exception as e:
        logger.error(f"Failed to apply cookies: {e}")
        return False


def perform_login(driver, wait, username, password):
    """Perform login with slow typing and save cookies"""
    try:
        logger.info("Starting login process...")
        
        # # Hardcoded credentials
        # username = "snrj2185@gmail.com"
        # password = "singhraj2185"
        
        # Add random delay before login
        time.sleep(random.uniform(2, 5))
        
        # Find and fill username with slow typing
        user_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
        user_input.clear()
        time.sleep(random.uniform(1, 2))
        slow_type(user_input, username)
        
        # Add delay between fields
        time.sleep(random.uniform(1, 3))
        
        # Find and fill password with slow typing
        pass_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
        pass_input.clear()
        time.sleep(random.uniform(1, 2))
        slow_type(pass_input, password)
        
        # Add delay before clicking submit
        time.sleep(random.uniform(2, 4))
        
        # Click login button
        sign_in_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        sign_in_btn.click()
        
        logger.info("Login form submitted")
        
        # Wait for login to complete
        timeout = 40
        elapsed = 0
        while 'feed' not in driver.current_url and elapsed < timeout:
            time.sleep(1)
            elapsed += 1
        
        if 'feed' in driver.current_url:
            logger.info("Login successful")
            # Save cookies after successful login
            save_cookies_to_cache(driver, expiry_hours=24)
            return True
        else:
            logger.error("Login failed - didn't reach feed page")
            return False
            
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return False


def check_login_status(driver):
    """Check if user is already logged in"""
    try:
        current_url = driver.current_url
        if 'feed' in current_url or 'linkedin.com/in/' in current_url:
            return True
        
        # Try to find elements that indicate logged-in state
        try:
            WebDriverWait(driver, 5).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-control-name='nav.settings']"))
                )
            )
            return True
        except:
            return False
            
    except Exception as e:
        logger.warning(f"Error checking login status: {e}")
        return False


def scout_leads(time_to_load, username, password, search_url : str = "", keywords: str = "") -> list:
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 10)

    like_btn_xpath = "//button[@data-reaction-details]"
    admin_xpath = "//div[@class='fie-impression-container']/div[@class='relative']/div[1]/div/div/a[1]"  # The one who posted the post
    leads_xpath = "//a[@rel='noopener noreferrer' and contains(@href, '/in')]"
    cross_btn = "(//button[@aria-label='Dismiss'])[1]"
    show_more_likes_xpath = "(//button[contains(@id,'ember') and contains(@class,'scaffold-finite-scroll__load-button')])[1]"
    input_xpath = "//input[@placeholder='Search']"
    post_button_xpath = "//button[text()='Posts' and ancestor::li[@class='search-reusables__primary-filter']]"

    leads_list = set()

    try:
        # Initial navigation with delay
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(random.uniform(3, 6))

        # Try to load cached cookies first
        cached_cookies = load_cookies_from_cache()
        login_required = True
        
        if cached_cookies:
            logger.info("Attempting to use cached cookies...")
            if apply_cookies_to_driver(driver, cached_cookies):
                # Navigate to feed to test cookies
                driver.get("https://www.linkedin.com/feed/")
                time.sleep(random.uniform(3, 5))
                
                # Check if login worked
                if check_login_status(driver):
                    logger.info("Successfully logged in using cached cookies")
                    login_required = False
                else:
                    logger.info("Cached cookies didn't work, proceeding with manual login")

        # Perform login if needed
        if login_required:
            # Navigate to login page
            driver.get("https://www.linkedin.com/login")
            time.sleep(random.uniform(2, 4))

            if not perform_login(driver, wait, username, password):
                logger.error("Login failed, exiting...")
                return []

        # Add delay after login
        time.sleep(random.uniform(3, 6))

        # Navigate to feed if not already there
        if 'feed' not in driver.current_url:
            driver.get("https://www.linkedin.com/feed/")
            time.sleep(random.uniform(3, 5))


        if not search_url:
            # --- SEARCH ---
            search_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, input_xpath)))
            search_input.clear()
            time.sleep(random.uniform(1, 2))
            slow_type(search_input, keywords)
            time.sleep(random.uniform(2, 4))
            search_input.send_keys(Keys.RETURN)
            time.sleep(random.uniform(3, 5))

            posts_btn = wait.until(EC.element_to_be_clickable((By.XPATH, post_button_xpath)))
            posts_btn.click()
            time.sleep(random.uniform(3, 5))
        else:
            driver.get(search_url)

        # --- SCROLL until enough posts are loaded ---
        try:
            start_time = time.time()
            end_time = time.time()
            while (end_time-start_time) < time_to_load:  # scroll till the given time
                like_elements = wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, like_btn_xpath))
                )
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                i = len(like_elements)
                end_time = time.time()
                logger.info(f"Posts loaded so far: {i}")
                time.sleep(random.uniform(4, 7))  # Increased delay


        except Exception as e:
            logger.warning(f"No like buttons found or error occurred: {e}")

        # --- LOOP through all the posts and collect url of admins ---
        try:
            admin_elements = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, admin_xpath))
            )
            for admin in admin_elements:
                try:
                    admin_url = admin.get_attribute("href")
                    if admin_url:
                        leads_list.add(admin_url)
                        logger.info(f"Found admin: {admin_url}")
                except Exception as e:
                    logger.warning(f"Error extracting admin URL: {e}")

        except Exception as e:
            logger.warning(f"Could not process admin buttons: {e}")

        # --- LOOP through all like buttons ---
        try:
            like_elements = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, like_btn_xpath))
            )
            print(f'Total posts found: {len(like_elements)}')

            for idx, like_btn in enumerate(like_elements, start=1):
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", like_btn)
                    time.sleep(random.uniform(2, 4))  # Increased delay

                    driver.execute_script("arguments[0].click();", like_btn)
                    logger.info(f"Opened likes popup for post {idx}")

                    time.sleep(random.uniform(3, 5))  # Increased delay

                    # Keep clicking "Show more results"
                    click_count = 0
                    while True:
                        try:
                            show_more_btn = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, show_more_likes_xpath))
                            )
                            logger.info("'Show more results' button found, clicking...")
                            driver.execute_script("arguments[0].click();", show_more_btn)
                            click_count += 1
                            logger.info(f"'Show more results' button clicked {click_count} time(s).")
                            time.sleep(random.uniform(6, 9))  # Increased delay
                        except Exception:
                            logger.info("No more 'Show more results' button found. Breaking loop.")
                            break

                    # Extract leads
                    leads = wait.until(EC.presence_of_all_elements_located((By.XPATH, leads_xpath)))
                    for lead in leads:
                        try:
                            lead_url = lead.get_attribute("href")
                            if lead_url and lead_url not in leads_list:
                                leads_list.add(lead_url)
                                logger.info(f"Found lead: {lead_url}")
                        except Exception as e:
                            logger.warning(f"Error extracting lead URL: {e}")

                    # Close popup
                    try:
                        close_btn = wait.until(EC.element_to_be_clickable((By.XPATH, cross_btn)))
                        close_btn.click()
                        time.sleep(random.uniform(2, 4))  # Increased delay
                    except:
                        logger.info("No dismiss button found, continuing...")

                    # Add delay between posts
                    time.sleep(random.uniform(3, 6))

                except Exception as e:
                    logger.warning(f"Error handling post {idx}: {e}")

        except Exception as e:
            logger.warning(f"Could not process posts: {e}")

        # --- Final list ---
        logger.info(f"Total unique leads collected: {len(leads_list)}")
        for lead in leads_list:
            if '/in/' in lead:
                lead_arr = lead.split('/')
                idx = lead_arr.index('in')
                lead_id = lead_arr[idx+1]
                if '?' in lead_id:
                    lead_id = lead_id.split('?')[0]
                lead_data = {"lead_id": lead_id, "linkedin_url": lead, "scraped": False}
                try:
                    supabase.table("all_leads").insert(lead_data).execute()
                except Exception as e:
                    logger.warning(f"Error inserting lead into Supabase: {e}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'leads_list_{timestamp}.csv'

        leads_df = pd.DataFrame(leads_list, columns=['LinkedIn Profile URL'])
        leads_df.to_csv(filename, index=False)
        print(f"Leads saved to {filename}")

        return list(leads_list)

    except Exception as e:
        logger.error(f"An error occurred during login or scraping: {e}")
        return []
    finally:
        time.sleep(random.uniform(5, 8))
        driver.quit()


# if __name__ == "__main__":
#     leads = scout_leads("https://www.linkedin.com/search/results/content/?fromOrganization=%5B%223185%22%5D&keywords=dreamforce&origin=GLOBAL_SEARCH_HEADER&sid=j4%3A&sortBy=%22relevance%22", "#dreamforce2025", 120, "rajs02073@gmail.com", "rajsingh7222")
#     print(f"Collected {len(leads)} leads")
