from openai import OpenAI
import requests
import base64
from datetime import datetime
from config import (
    OPENAI_API_KEY, 
    TWITTER_CONSUMER_KEY, 
    TWITTER_CONSUMER_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    MAX_TWEET_LENGTH,
    logger
)

class SocialPoster:
    def __init__(self):
        self.client = None
        self.twitter_available = False
        self.bearer_token = None
        
        try:
            if not OPENAI_API_KEY:
                logger.error("OPENAI_API_KEY is missing")
                raise ValueError("OPENAI_API_KEY is missing")
            
            if not OPENAI_API_KEY.startswith('sk-'):
                logger.error("Invalid API key format - should start with 'sk-'")
                raise ValueError("Invalid API key format")
            
            # Initialize OpenAI client
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            
            # Test the connection with a simple request
            logger.info("Testing OpenAI connection...")
            test_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=5
            )
            
            logger.info("OpenAI API configured successfully")
            
            # Setup Twitter (optional)
            self.setup_twitter()
            
        except Exception as e:
            logger.error(f"SocialPoster initialization failed: {str(e)}")
            raise

    def setup_twitter(self):
        try:
            if not all([TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
                logger.warning("Twitter API keys missing - Twitter features disabled")
                return
            
            self.bearer_token = self._get_bearer_token()
            
            if self.bearer_token and self._test_twitter():
                self.twitter_available = True
                logger.info("Twitter API configured")
            else:
                logger.warning("Twitter setup failed - posting disabled")
                
        except Exception as e:
            logger.error(f"Twitter setup error: {e}")

    def _get_bearer_token(self):
        try:
            credentials = f"{TWITTER_CONSUMER_KEY}:{TWITTER_CONSUMER_SECRET}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
            }
            
            response = requests.post(
                'https://api.twitter.com/oauth2/token',
                headers=headers,
                data={'grant_type': 'client_credentials'}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get('access_token')
            else:
                logger.error(f"Bearer token request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting bearer token: {e}")
            return None

    def _test_twitter(self):
        try:
            if not self.bearer_token:
                return False
            
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            
            response = requests.get(
                'https://api.twitter.com/2/users/me',
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Twitter API test successful - User ID: {user_data.get('data', {}).get('id')}")
                return True
            else:
                logger.warning(f"Twitter API test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Twitter API test error: {e}")
            return False

    def generate_content(self, hotels, destination="Jakarta"):
        """Generate social media content using OpenAI"""
        try:
            if not self.client:
                logger.error("OpenAI client not available")
                return self._create_fallback_content(destination, hotels)
                
            if not hotels:
                logger.warning("No hotels data provided for content generation")
                return self._create_fallback_content(destination, [])
            
            logger.info(f"Generating content for {len(hotels)} hotels in {destination}")
            
            # Prepare hotel information for the prompt
            hotel_list = ""
            for i, hotel in enumerate(hotels[:3], 1):
                hotel_name = hotel.get('name', 'Unknown Hotel')
                hotel_price = hotel.get('price', 'Price not available')
                hotel_list += f"{i}. {hotel_name} - {hotel_price}\n"
            
            prompt = f"""
            Create an engaging social media post in Indonesian about these hotels in {destination}:

            Hotels found:
            {hotel_list}

            Requirements:
            - Maximum 280 characters (for Twitter)
            - Use relevant emojis
            - Make it attractive and encourage travel
            - Include a call to action
            - Add 2-3 relevant hashtags
            - Use natural, friendly language
            - Do not mention the data source (Traveloka)
            - Focus on the travel experience and hotel quality

            Format:
            [Main caption with emojis]
            [Hashtags]
            """
            
            logger.info(f"Sending request to OpenAI with {len(hotels)} hotels")
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=200,
                temperature=0.8,
                timeout=30
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"Raw OpenAI response: {content}")
            
            content = self._clean_content(content)
            logger.info(f"Content generated successfully: {len(content)} characters")
            
            return content
            
        except Exception as e:
            logger.error(f"Content generation error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return self._create_fallback_content(destination, hotels)

    def _clean_content(self, content):
        """Clean and format content for social media"""
        # Remove extra whitespace and clean up formatting
        content = ' '.join(content.split())
        content = content.replace('"', '').replace('`', "'")
        
        # Ensure it ends properly
        content = content.strip()
        
        # Truncate if too long
        if len(content) > MAX_TWEET_LENGTH:
            content = content[:MAX_TWEET_LENGTH-3] + "..."
        
        return content

    def _create_fallback_content(self, destination, hotels):
        """Create fallback content when AI generation fails"""
        try:
            if hotels:
                hotel_names = [hotel.get('name', 'Hotel') for hotel in hotels[:2]]
                content = f"Temukan hotel menarik di {destination}!\n\n"
                content += f"⭐ {', '.join(hotel_names)}\n\n"
                content += "Perfect untuk liburan Anda berikutnya!\n\n"
                content += f"#Hotel{destination.replace(' ', '')} #Travel #Liburan"
            else:
                content = f"Jelajahi hotel terbaik di {destination}! 🏨\n\n"
                content += "Temukan penginapan perfect untuk perjalanan Anda.\n\n"
                content += f"#Travel{destination.replace(' ', '')} #Hotel #Wisata"
            
            # Ensure it's within Twitter limits
            if len(content) > MAX_TWEET_LENGTH:
                content = content[:MAX_TWEET_LENGTH-3] + "..."
            
            logger.info("Using fallback content")
            return content
            
        except Exception as e:
            logger.error(f"Fallback content creation failed: {e}")
            return f"Discover amazing hotels in {destination}! #Travel #Hotels"

    def publish_to_twitter(self, content):
        """Post content to Twitter (with free tier limitations)"""
        try:
            if not self.twitter_available:
                logger.warning("Twitter not available - showing manual posting instructions")
                return {
                    "success": True,
                    "message": "Content ready for manual posting",
                    "content": content,
                    "character_count": len(content),
                    "note": "With free tier, post this content manually to Twitter/X"
                }
            
            # For free tier, we can only show the content to post manually
            logger.info("Twitter content ready for posting:")
            logger.info(f"TWEET: {content}")
            
            return {
                "success": True,
                "message": "Content generated successfully",
                "content": content,
                "character_count": len(content),
                "note": "Post this content manually to Twitter/X"
            }
            
        except Exception as e:
            logger.error(f"Twitter posting error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Twitter posting failed"
            }

    def publish_content(self, hotels, destination="Jakarta"):
        """Publish content to social media"""
        try:
            if not hotels:
                return {
                    "success": False,
                    "error": "No hotel data available",
                    "message": "Please scrape hotels first"
                }
            
            logger.info(f"Starting content publishing for {destination}")
            
            # Generate content
            content = self.generate_content(hotels, destination)
            
            # Try to post to Twitter
            twitter_result = self.publish_to_twitter(content)
            
            result = {
                "content_generation": {
                    "success": True,
                    "content": content,
                    "character_count": len(content)
                },
                "twitter": twitter_result,
                "destination": destination,
                "hotel_count": len(hotels),
                "overall_success": True
            }
            
            logger.info("Content publishing completed")
            return result
            
        except Exception as e:
            logger.error(f"Publishing error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Publishing failed"
            }

    def generate_caption_only(self, hotels, destination="Jakarta"):
        """Generate caption only without posting"""
        try:
            if not hotels:
                return {
                    "success": False,
                    "error": "No hotel data available",
                    "message": "Please scrape hotels first"
                }
            
            content = self.generate_content(hotels, destination)
            
            return {
                "success": True,
                "content": content,
                "character_count": len(content),
                "destination": destination,
                "hotel_count": len(hotels)
            }
            
        except Exception as e:
            logger.error(f"Caption generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Caption generation failed"
            }

# Initialize SocialPoster instance
try:
    social_poster = SocialPoster()
    logger.info("SocialPoster initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize SocialPoster: {e}")
    social_poster = None

# Convenience functions
def generate_content(hotels, destination="Jakarta"):
    if not social_poster:
        logger.error("SocialPoster not available")
        return "AI service not available"
    return social_poster.generate_content(hotels, destination)

def publish_to_social_media(hotels, destination="Jakarta"):
    if not social_poster:
        return {
            "success": False,
            "error": "AI service not available",
            "message": "Please check OpenAI API configuration"
        }
    return social_poster.publish_content(hotels, destination)

def generate_caption(hotels, destination="Jakarta"):
    if not social_poster:
        return {
            "success": False,
            "error": "AI service not available", 
            "message": "Please check OpenAI API configuration"
        }
    return social_poster.generate_caption_only(hotels, destination)