from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import schedule
import time
from datetime import datetime

from config import logger, FLASK_HOST, FLASK_PORT, DEFAULT_DESTINATION, config_valid
from scraper import scrape_hotels
from social_poster import publish_to_social_media, generate_caption, social_poster

app = Flask(__name__)
CORS(app)

hotels_data = []

def validate_json_request():
    if not request.is_json:
        return False, "Content-Type must be application/json"
    
    try:
        request.get_json()
        return True, "Valid JSON"
    except Exception as e:
        return False, f"Invalid JSON: {str(e)}"

@app.route('/')
def home():
    return jsonify({
        "message": "Hotel Scraper API",
        "version": "4.1",
        "source": "Traveloka",
        "openai_available": social_poster is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "hotels_count": len(hotels_data),
        "openai_available": social_poster is not None,
        "config_valid": config_valid
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
        is_valid, message = validate_json_request()
        if not is_valid:
            return jsonify({"success": False, "error": message}), 400
        
        data = request.get_json() or {}
        destination = data.get('destination', DEFAULT_DESTINATION)
        
        global hotels_data
        hotels = scrape_hotels(destination)
        hotels_data = hotels
        
        return jsonify({
            "success": True,
            "destination": destination,
            "count": len(hotels),
            "hotels": hotels
        })
        
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate_endpoint():
    try:
        is_valid, message = validate_json_request()
        if not is_valid:
            return jsonify({"success": False, "error": message}), 400
        
        if not social_poster:
            return jsonify({
                "success": False,
                "error": "AI service unavailable",
                "message": "Check API configuration"
            }), 500
        
        data = request.get_json() or {}
        destination = data.get('destination', DEFAULT_DESTINATION)
        
        if not hotels_data:
            return jsonify({
                "success": False,
                "error": "No hotel data",
                "message": "Scrape hotels first"
            }), 400
        
        result = generate_caption(hotels_data, destination)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/publish', methods=['POST'])
def publish_endpoint():
    try:
        is_valid, message = validate_json_request()
        if not is_valid:
            return jsonify({"success": False, "error": message}), 400
        
        data = request.get_json() or {}
        destination = data.get('destination', DEFAULT_DESTINATION)
        
        result = publish_to_social_media(hotels_data, destination)
        
        if isinstance(result, dict):
            return jsonify(result)
        else:
            return jsonify({
                "success": bool(result),
                "message": "Content published" if result else "Publish failed",
                "destination": destination,
                "hotel_count": len(hotels_data)
            })
        
    except Exception as e:
        logger.error(f"Publish error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/chatbot', methods=['POST'])
def chatbot():
    try:
        is_valid, message = validate_json_request()
        if not is_valid:
            return jsonify({"success": False, "error": message}), 400
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"success": False, "error": "Message required"}), 400
        
        message_text = data['message'].lower()
        
        if any(word in message_text for word in ['hotel', 'penginapan', 'menginap']):
            response = f"Found {len(hotels_data)} hotels. Use /hotels endpoint to view."
        elif any(word in message_text for word in ['harga', 'price', 'murah']):
            response = "Check Traveloka for latest prices and deals."
        elif any(word in message_text for word in ['traveloka', 'expedia', 'booking']):
            response = "Currently scraping from Traveloka. Want me to scrape hotels for specific destination?"
        else:
            response = "I'm a hotel assistant. I can help find hotel info and generate social media content."
        
        return jsonify({
            "success": True,
            "response": response,
            "hotel_data_available": len(hotels_data) > 0
        })
        
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return jsonify({
            "success": False,
            "error": "Service unavailable, try again later."
        }), 500

def run_scheduler():
    schedule.every(6).hours.do(lambda: update_hotels_data(DEFAULT_DESTINATION))
    schedule.every(12).hours.do(lambda: auto_publish_content())
    
    logger.info("Scheduler started")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(300)

def update_hotels_data(destination):
    global hotels_data
    try:
        hotels = scrape_hotels(destination)
        hotels_data = hotels
        logger.info(f"Auto updated: {len(hotels)} hotels")
    except Exception as e:
        logger.error(f"Auto update failed: {e}")

def auto_publish_content():
    global hotels_data
    try:
        if hotels_data:
            success = publish_to_social_media(hotels_data, DEFAULT_DESTINATION)
            if success:
                logger.info("Auto published content")
            else:
                logger.error("Auto publish failed")
        else:
            logger.warning("No data to auto publish")
    except Exception as e:
        logger.error(f"Auto publish error: {e}")

def main():
    try:
        logger.info("Starting Hotel Scraper API")
        
        if not config_valid:
            logger.warning("Configuration issues detected")
        
        global hotels_data
        hotels = scrape_hotels(DEFAULT_DESTINATION)
        hotels_data = hotels
        logger.info(f"Initial scrape: {len(hotels)} hotels")
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Scheduler started")
        
        logger.info(f"Starting on {FLASK_HOST}:{FLASK_PORT}")
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")

if __name__ == "__main__":
    main()