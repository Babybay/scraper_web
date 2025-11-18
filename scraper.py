from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import time
import random
from datetime import datetime
from config import logger

class HotelScraper:
    def __init__(self):
        self.driver = None
    
    def setup_driver(self):
        try:
            options = Options()
            options.add_argument('--no-first-run')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
            
            selected_agent = random.choice(user_agents)
            options.add_argument(f'--user-agent={selected_agent}')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            stealth(self.driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    fix_hairline=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Driver setup failed: {e}")
            return False
    
    def random_delay(self, min_sec=2, max_sec=5):
        time.sleep(random.uniform(min_sec, max_sec))
    
    def scroll_page(self):
        try:
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            for i in range(random.randint(2, 3)):
                scroll_height = total_height * random.uniform(0.2, 0.5)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_height});")
                time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")
    
    def scrape_traveloka(self, destination="Jakarta"):
        hotels = []
        
        try:
            if not self.setup_driver():
                return []
            
            url = f"https://www.traveloka.com/en-id/hotel/search?spec={destination.replace(' ', '%20')}"
            logger.info(f"Scraping: {url}")
            
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            self.random_delay(3, 6)
            self.scroll_page()
            self.random_delay(2, 4)
            
            hotels = self.extract_hotels()
            logger.info(f"Extracted {len(hotels)} hotels")
            return hotels
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return []
        finally:
            self.cleanup()
    
    def extract_hotels(self):
        hotels = []
        
        try:
            selectors = [
                '[data-testid="hotel-card"]',
                '.tvat-hotelCard',
                'div[class*="hotel-card"]'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements[:6]:
                            hotel_data = self.extract_hotel_data(element)
                            if hotel_data and hotel_data.get('name'):
                                hotels.append(hotel_data)
                        break
                except:
                    continue
            
            if not hotels:
                hotels = self.fallback_extraction()
                
        except Exception as e:
            logger.error(f"Extraction error: {e}")
        
        return hotels
    
    def extract_hotel_data(self, element):
        hotel_data = {}
        
        try:
            name_selectors = ['[data-testid="hotel-name"]', '.tvat-hotelName', 'h3']
            for selector in name_selectors:
                try:
                    name_elem = element.find_element(By.CSS_SELECTOR, selector)
                    name = name_elem.text.strip()
                    if name and len(name) > 3:
                        hotel_data['name'] = name
                        break
                except:
                    continue
            
            price_selectors = ['[data-testid="price"]', '.tvat-price', '[class*="price"]']
            for selector in price_selectors:
                try:
                    price_elem = element.find_element(By.CSS_SELECTOR, selector)
                    price = price_elem.text.strip()
                    if price and any(c.isdigit() for c in price):
                        hotel_data['price'] = price
                        break
                except:
                    continue
            
            if hotel_data.get('name'):
                hotel_data['source'] = 'Traveloka'
                hotel_data['scraped_at'] = datetime.now().isoformat()
                
        except Exception as e:
            logger.warning(f"Hotel data extraction failed: {e}")
        
        return hotel_data
    
    def fallback_extraction(self):
        hotels = []
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            
            current_hotel = {}
            for line in lines:
                if len(line) < 10 or len(line) > 100:
                    continue
                    
                if any(keyword in line.lower() for keyword in ['hotel', 'resort', 'inn']):
                    if not current_hotel.get('name'):
                        current_hotel['name'] = line
                        current_hotel['source'] = 'Traveloka'
                elif any(price_indicator in line.lower() for price_indicator in ['rp', 'idr']):
                    if current_hotel.get('name') and not current_hotel.get('price'):
                        current_hotel['price'] = line
                
                if current_hotel.get('name') and current_hotel.get('price'):
                    hotels.append(current_hotel.copy())
                    current_hotel = {}
                    
        except Exception as e:
            logger.warning(f"Fallback extraction failed: {e}")
        
        return hotels
    
    def scrape_with_retry(self, destination="Jakarta", max_retries=2):
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1} for {destination}")
                hotels = self.scrape_traveloka(destination)
                if hotels:
                    return hotels
                else:
                    logger.warning(f"Attempt {attempt + 1}: No hotels found")
                    if attempt < max_retries - 1:
                        time.sleep((attempt + 1) * 10)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 10)
        
        return []
    
    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")

hotel_scraper = HotelScraper()

def scrape_hotels(destination="Jakarta"):
    return hotel_scraper.scrape_with_retry(destination)