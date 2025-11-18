from flask import Flask, jsonify, request
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import threading
import schedule
import time
import tweepy
import openai
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
hotels_data = []

# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Setup Twitter API
consumer_key = os.getenv("TW_CONSUMER_KEY")
consumer_secret = os.getenv("TW_CONSUMER_SECRET")
access_token = os.getenv("TW_ACCESS_TOKEN")
access_token_secret = os.getenv("TW_ACCESS_TOKEN_SECRET")

# Initialize Twitter API
try:
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    twitter_api = tweepy.API(auth, wait_on_rate_limit=True)
    logger.info("Twitter API initialized successfully")
except Exception as e:
    logger.error(f"Twitter API initialization failed: {e}")
    twitter_api = None

def get_future_dates(days_from_now=7, stay_days=6):
    """Generate future dates for hotel search"""
    start_date = datetime.now() + timedelta(days=days_from_now)
    end_date = start_date + timedelta(days=stay_days)
    
    return {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'checkin': start_date.strftime('%Y-%m-%d'),
        'checkout': end_date.strftime('%Y-%m-%d')
    }

def build_expedia_url(destination, region_id=None):
    """Build Expedia URL dengan parameter yang tepat"""
    dates = get_future_dates()
    
    base_params = {
        'adults': 2,
        'children': '',
        'd1': dates['start_date'],  # Check-in
        'd2': dates['end_date'],    # Check-out
        'startDate': dates['start_date'],
        'endDate': dates['end_date'],
        'rooms': 1,
        'sort': 'RECOMMENDED',
        'useRewards': 'false'
    }
    
    if region_id:
        base_params['regionId'] = region_id
        base_params['destination'] = f"{destination}%2C%20Indonesia"
    else:
        base_params['destination'] = destination.replace(' ', '%20')
    
    # Build URL
    url = "https://www.expedia.co.id/Hotel-Search?"
    params = [f"{key}={value}" for key, value in base_params.items()]
    url += "&".join(params)
    
    return url

def setup_selenium_driver():
    """Setup Chrome driver dengan options untuk menghindari deteksi"""
    chrome_options = Options()
    
    # Headless options
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Random user agents
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        logger.error(f"Failed to setup Chrome driver: {e}")
        return None

def scrape_expedia_hotels(destination="Bali"):
    """Scrape hotel data dari Expedia.co.id dengan Selenium"""
    driver = None
    
    # Region IDs untuk destinasi populer di Indonesia
    region_ids = {
        'bali': '602651',
        'jakarta': '178234',
        'yogyakarta': '181994',
        'bandung': '178296',
        'surabaya': '178276'
    }
    
    destination_lower = destination.lower()
    region_id = None
    for key, rid in region_ids.items():
        if key in destination_lower:
            region_id = rid
            break
    
    try:
        driver = setup_selenium_driver()
        if not driver:
            return []
        
        # Build URL
        url = build_expedia_url(destination, region_id)
        logger.info(f"Scraping URL: {url}")
        
        driver.get(url)
        
        # Tunggu dengan berbagai strategi
        wait = WebDriverWait(driver, 20)
        
        # Tunggu sampai ada element hotel
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-stid="property-listing-results"]')))
        except TimeoutException:
            logger.warning("Property listing results not found, continuing anyway")
        
        time.sleep(8)  # Additional wait for dynamic content
        
        hotels = []
        
        # Multiple strategies untuk find hotel elements
        selectors = [
            '[data-stid="property-card"]',
            '[data-testid="property-card"]',
            '.uitk-card.uitk-card-roundcorner-all',
            'div[data-stid="property-card-container"]'
        ]
        
        hotel_elements = []
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Found {len(elements)} hotels with selector: {selector}")
                    hotel_elements = elements
                    break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        if not hotel_elements:
            logger.warning("No hotel elements found with any selector")
            return []
        
        for element in hotel_elements[:12]:  # Limit to 12 hotels
            try:
                hotel_info = extract_hotel_data(element)
                if hotel_info and hotel_info.get('name'):
                    hotels.append(hotel_info)
                    
            except Exception as e:
                logger.error(f"Error processing hotel element: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(hotels)} hotels from {destination}")
        return hotels
        
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def extract_hotel_data(element):
    """Extract data dari hotel element"""
    hotel_info = {}
    
    try:
        # Extract hotel name
        name_selectors = [
            '[data-stid="property-link"]',
            'h3',
            '.uitk-heading.uitk-heading-5',
            '[data-testid="hotel-name"]'
        ]
        
        for selector in name_selectors:
            try:
                name_element = element.find_element(By.CSS_SELECTOR, selector)
                name = name_element.text.strip()
                if name and len(name) > 3:
                    hotel_info['name'] = name
                    break
            except:
                continue
        
        # Extract price
        price_selectors = [
            '[data-stid="price-lockup-text"]',
            '.uitk-price',
            '[aria-label*="price"]',
            '[class*="price"]'
        ]
        
        for selector in price_selectors:
            try:
                price_element = element.find_element(By.CSS_SELECTOR, selector)
                price = price_element.text.strip()
                if price and any(c.isdigit() for c in price):
                    hotel_info['price'] = price
                    break
            except:
                continue
        
        # Extract rating
        rating_selectors = [
            '[aria-label*="bintang"]',
            '[aria-label*="star"]',
            '[aria-label*="rating"]',
            '.uitk-badge.uitk-badge-small'
        ]
        
        for selector in rating_selectors:
            try:
                rating_element = element.find_element(By.CSS_SELECTOR, selector)
                rating = rating_element.get_attribute('aria-label') or rating_element.text.strip()
                if rating:
                    hotel_info['rating'] = rating
                    break
            except:
                continue
        
        # Extract location
        location_selectors = [
            '[data-stid="location"]',
            '[class*="location"]',
            '.uitk-text.uitk-type-300'
        ]
        
        for selector in location_selectors:
            try:
                location_element = element.find_element(By.CSS_SELECTOR, selector)
                location = location_element.text.strip()
                if location and len(location) > 5:
                    hotel_info['location'] = location
                    break
            except:
                continue
        
        if hotel_info.get('name'):
            hotel_info['source'] = 'Expedia.co.id'
            hotel_info['scraped_at'] = datetime.now().isoformat()
            logger.info(f"✅ Scraped: {hotel_info['name']}")
            
        return hotel_info
        
    except Exception as e:
        logger.error(f"Error extracting hotel data: {e}")
        return None

def scrape_hotels(destination="Bali"):
    """Main scraping function"""
    global hotels_data
    try:
        hotels = scrape_expedia_hotels(destination)
        hotels_data = hotels
        return hotels
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        hotels_data = []
        return []

def generate_content(hotels, destination="Bali"):
    """Generate content menggunakan OpenAI"""
    try:
        if not hotels:
            return f"Tidak menemukan data hotel untuk {destination}. Coba destinasi lain."
        
        # Prepare hotel information
        hotel_list = "\n".join([f"🏨 {hotel['name']} - {hotel.get('price', 'Cek harga')}" for hotel in hotels[:3]])
        
        prompt = f"""
        Buat postingan media sosial dalam Bahasa Indonesia tentang penemuan hotel di {destination}:

        Hotel yang ditemukan:
        {hotel_list}

        Requirements:
        - Maksimal 280 karakter (untuk Twitter)
        - Gunakan emoji yang relevan
        - Buat menarik dan mengajak traveling
        - Sebutkan sumber: Expedia.co.id
        - Sertakan call to action
        - Tambahkan 2-3 hashtag

        Postingan:
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        return content
        
    except Exception as e:
        logger.error(f"Content generation error: {e}")
        # Fallback content
        if hotels:
            hotel_names = [hotel['name'] for hotel in hotels[:2]]
            return f"🏨 TEMUKAN DEAL HOTEL MENARIK DI {destination.upper()}! ✨\n\n{', '.join(hotel_names)}\n\nCek harga terbaru di Expedia.co.id! 🎯\n\n#HotelDeals #Travel{destination}"
        return f"Jelajahi hotel terbaik di {destination}! 🏨✈️"

def publish_to_twitter(content):
    """Publish content to Twitter"""
    try:
        if not twitter_api:
            logger.error("Twitter API not available")
            return False
        
        # Pastikan content tidak lebih dari 280 karakter
        if len(content) > 280:
            content = content[:277] + "..."
        
        tweet = twitter_api.update_status(content)
        logger.info(f"✅ Posted to Twitter: {tweet.id}")
        return True
        
    except tweepy.TweepyException as e:
        logger.error(f"Twitter posting failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in Twitter posting: {e}")
        return False

def publish_content():
    """Publish content to social media"""
    global hotels_data
    
    if not hotels_data:
        logger.warning("No hotel data to publish")
        return False
    
    try:
        destination = hotels_data[0].get('destination', 'Bali') if hotels_data else 'Bali'
        content = generate_content(hotels_data, destination)
        logger.info(f"Generated content: {content}")
        
        # Post to Twitter
        success = publish_to_twitter(content)
        
        if success:
            logger.info("✅ Content published to Twitter successfully")
            return True
        else:
            logger.error("❌ Failed to publish to Twitter")
            return False
        
    except Exception as e:
        logger.error(f"Publishing error: {e}")
        return False

# Flask Routes
@app.route('/')
def home():
    return jsonify({
        "message": "Hotel Scraper API is running!",
        "version": "2.0",
        "source": "Expedia.co.id",
        "endpoints": {
            "hotels": "GET /hotels",
            "scrape": "POST /scrape",
            "generate": "POST /generate", 
            "publish": "POST /publish",
            "chatbot": "POST /chatbot"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "hotels_count": len(hotels_data)
    })

@app.route('/hotels', methods=['GET'])
def get_hotels():
    return jsonify({
        "success": True,
        "count": len(hotels_data),
        "hotels": hotels_data,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    try:
        data = request.get_json() or {}
        destination = data.get('destination', 'Bali')
        
        hotels = scrape_hotels(destination)
        
        return jsonify({
            "success": True,
            "destination": destination,
            "count": len(hotels),
            "hotels": hotels,
            "message": f"Scraped {len(hotels)} hotels from Expedia.co.id"
        })
        
    except Exception as e:
        logger.error(f"Scraping endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/generate', methods=['POST'])
def generate_endpoint():
    try:
        data = request.get_json() or {}
        destination = data.get('destination', 'Bali')
        
        content = generate_content(hotels_data, destination)
        
        return jsonify({
            "success": True,
            "content": content,
            "character_count": len(content),
            "hotel_count": len(hotels_data)
        })
        
    except Exception as e:
        logger.error(f"Generation endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/publish', methods=['POST'])
def publish_endpoint():
    try:
        success = publish_content()
        
        return jsonify({
            "success": success,
            "message": "Content published to Twitter successfully" if success else "Failed to publish content",
            "hotel_count": len(hotels_data)
        })
        
    except Exception as e:
        logger.error(f"Publish endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/chatbot', methods=['POST'])
def chatbot():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"success": False, "error": "Message is required"}), 400
        
        message = data['message']
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Anda adalah asisten travel yang membantu mencari informasi hotel dan destinasi wisata di Indonesia."},
                {"role": "user", "content": message}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content.strip()
        
        return jsonify({
            "success": True,
            "response": reply,
            "hotel_data_available": len(hotels_data) > 0
        })
        
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return jsonify({
            "success": False,
            "error": "Maaf, sedang ada gangguan. Silakan coba lagi."
        }), 500

def run_scheduler():
    """Run scheduled tasks"""
    # Schedule scraping every 4 hours
    schedule.every(4).hours.do(lambda: scrape_hotels("Bali"))
    
    # Schedule publishing every 8 hours
    schedule.every(8).hours.do(publish_content)
    
    logger.info("✅ Scheduler started")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(300)

def main():
    """Main function"""
    try:
        # Initial scrape
        logger.info("🚀 Starting initial scrape...")
        scrape_hotels("Bali")
        
        # Start scheduler
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("✅ Scheduler thread started")
        
        # Start Flask app
        logger.info("🌐 Starting Flask application...")
        app.run(host="0.0.0.0", port=5000, debug=False)
        
    except Exception as e:
        logger.error(f"❌ Application failed to start: {e}")

if __name__ == "__main__":
    main()