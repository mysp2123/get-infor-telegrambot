import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # News APIs (free endpoints)
    GUARDIAN_API_KEY = os.getenv('GUARDIAN_API_KEY')
    
    # AI Services - Multiple Gemini API Keys for rotation (comma-separated)
    GOOGLE_AI_API_KEYS = [
        key.strip() for key in os.getenv('GOOGLE_AI_API_KEY', '').split(',') 
        if key.strip()
    ]
    
    # Facebook API - Graph API with Access Token  
    FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
    FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')  # Working Page Access Token
    FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')
    
    # Facebook Automation (Selenium) - Fallback option
    FACEBOOK_EMAIL = os.getenv('FACEBOOK_EMAIL')
    FACEBOOK_PASSWORD = os.getenv('FACEBOOK_PASSWORD')
    FACEBOOK_PAGE_NAME = os.getenv('FACEBOOK_PAGE_NAME', 'PioneerX Update News')
    
    # Selenium Configuration
    SELENIUM_HEADLESS = os.getenv('SELENIUM_HEADLESS', 'false')
    SELENIUM_TIMEOUT = int(os.getenv('SELENIUM_TIMEOUT', '30'))
    CHROME_BINARY_PATH = os.getenv('CHROME_BINARY_PATH', '')
    
    # Image Generation APIs - Multiple keys for failover (comma-separated)
    STABILITY_API_KEYS = [
        key.strip() for key in os.getenv('STABILITY_API_KEY', '').split(',') 
        if key.strip()
    ]
    
    HUGGING_FACE_API_KEYS = [
        os.getenv('HUGGING_FACE_API_KEY', ''),
        os.getenv('HUGGING_FACE_API_KEY_2', ''),
    ]
    
    DEEPAI_API_KEYS = [
        os.getenv('DEEPAI_API_KEY', ''),
        os.getenv('DEEPAI_API_KEY_2', ''),
    ]
    
    REPLICATE_API_TOKENS = [
        os.getenv('REPLICATE_API_TOKEN', ''),
        os.getenv('REPLICATE_API_TOKEN_2', ''),
    ]
    
    # Web Scraping Settings
    SCRAPING_USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    
    # Google Sheets
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')
    GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
    
    # Expert Facebook Profile
    EXPERT_FACEBOOK_URL = os.getenv('USER_PROFILE_URL', "https://www.facebook.com/tuanqho")
    EXPERT_NAME = "Ho Quoc Tuan"
    
    # Keywords for relevance scoring - Focus on Economics & International Politics
    RELEVANCE_KEYWORDS = [
        # Core political figures & leaders
        "Trump", "Biden", "Xi Jinping", "Putin", "Zelensky",
        
        # International & Trade
        "US", "USA", "America", "China", "Europe", "international", "global", 
        "trade", "tariffs", "sanctions", "diplomatic", "foreign policy",
        
        # Economics & Markets
        "economy", "economic", "business", "market", "inflation", "recession",
        "GDP", "growth", "investment", "stock", "currency", "interest rates",
        
        # Government & Politics
        "government", "politics", "policy", "election", "congress", "parliament"
    ]
    
    # Appeal keywords for scoring
    APPEAL_KEYWORDS = ["breaking", "exclusive", "urgent", "major", "crisis", "historic", "unprecedented", "dramatic"]
    
    # Vietnamese language settings
    LANGUAGE = "vi"
    
    # Image settings
    IMAGE_RATIO = "16:9"
    LOGO_PATH = os.getenv('PIONEERX_LOGO_PATH', "assets/PioneerX-logo.JPG")

    @classmethod
    def get_active_api_keys(cls, service_name: str) -> list:
        """Lấy danh sách API keys hợp lệ cho service"""
        if service_name == 'stability':
            return [key for key in cls.STABILITY_API_KEYS if key and key.strip()]
        elif service_name == 'huggingface':
            return [key for key in cls.HUGGING_FACE_API_KEYS if key and key.strip()]
        elif service_name == 'deepai':
            return [key for key in cls.DEEPAI_API_KEYS if key and key.strip()]
        elif service_name == 'replicate':
            return [key for key in cls.REPLICATE_API_TOKENS if key and key.strip()]
        elif service_name == 'google' or service_name == 'gemini':
            return [key for key in cls.GOOGLE_AI_API_KEYS if key and key.strip()]
        return []
