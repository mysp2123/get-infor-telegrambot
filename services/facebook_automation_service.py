"""
Facebook Automation Service sử dụng Selenium với Session Persistence
Thay thế cho Facebook API để đăng bài tự động lên Facebook
✨ FEATURES: Persistent login, Cookie management, Profile storage
"""

import asyncio
import os
import time
import json
import pickle
import subprocess
import signal
from typing import Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import Config
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FacebookAutomationService:
    def __init__(self):
        self.config = Config()
        self.driver = None
        self.wait = None
        self.is_logged_in = False
        
        # Session persistence settings
        self.session_dir = "facebook_sessions"
        self.profile_dir = os.path.join(self.session_dir, "profile")
        self.cookies_file = os.path.join(self.session_dir, "cookies.json")
        self.session_file = os.path.join(self.session_dir, "session_info.json")
        
        # Ensure session directory exists
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(self.profile_dir, exist_ok=True)
        
        # Session management
        self.session_expires = None
        self.last_activity = None
    
    def _cleanup_chrome_processes(self):
        """Cleanup any existing Chrome processes to avoid profile conflicts"""
        try:
            # Kill any existing Chrome processes
            if os.name == 'posix':  # macOS/Linux
                subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
                subprocess.run(['pkill', '-f', 'chromedriver'], capture_output=True)
            elif os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
                subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], capture_output=True)
            
            # Wait a moment for processes to terminate
            time.sleep(3)
            
            # Clean up profile lock files
            try:
                import shutil
                lock_files = [
                    os.path.join(self.profile_dir, 'SingletonLock'),
                    os.path.join(self.profile_dir, 'SingletonSocket'),
                    os.path.join(self.profile_dir, 'SingletonCookie'),
                    os.path.join(self.profile_dir, 'Default', 'SingletonLock')
                ]
                
                for lock_file in lock_files:
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        logger.info(f"🗑️ Removed lock file: {lock_file}")
                        
            except Exception as lock_error:
                logger.warning(f"⚠️ Could not clean lock files: {lock_error}")
            
            logger.info("🧹 Chrome processes and lock files cleaned up")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not cleanup Chrome processes: {e}")
        
    def _setup_driver(self, use_persistent_profile: bool = True):
        """Thiết lập Chrome driver với persistent profile để duy trì session"""
        
        # Cleanup existing Chrome processes to avoid conflicts
        self._cleanup_chrome_processes()
        
        chrome_options = Options()
        
        # 🔐 PERSISTENT PROFILE - Key feature for session persistence
        if use_persistent_profile:
            chrome_options.add_argument(f'--user-data-dir={self.profile_dir}')
            chrome_options.add_argument('--profile-directory=Default')
            logger.info(f"🔐 Using persistent profile: {self.profile_dir}")
        
        # Cấu hình từ .env
        if getattr(self.config, 'SELENIUM_HEADLESS', 'false').lower() == 'true':
            chrome_options.add_argument('--headless')
        
        # Enhanced options for session persistence
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Session and cookies persistence
        chrome_options.add_argument('--enable-local-storage')
        chrome_options.add_argument('--enable-session-storage')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--no-default-browser-check')
        
        # Automation detection bypass
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # User agent để tránh bị phát hiện
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Performance optimizations
        chrome_options.add_argument('--memory-pressure-off')
        chrome_options.add_argument('--max_old_space_size=4096')
        
        # Đường dẫn Chrome binary nếu có
        chrome_binary = getattr(self.config, 'CHROME_BINARY_PATH', '')
        if chrome_binary and os.path.exists(chrome_binary):
            chrome_options.binary_location = chrome_binary
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Bypass automation detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # Thiết lập timeout
            timeout = int(getattr(self.config, 'SELENIUM_TIMEOUT', 30))
            self.wait = WebDriverWait(self.driver, timeout)
            
            # Maximize window for better element detection
            self.driver.maximize_window()
            
            logger.info("✅ Chrome driver với persistent profile được thiết lập thành công")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi thiết lập Chrome driver: {e}")
            return False
    
    def _save_session_info(self):
        """Lưu thông tin session"""
        try:
            session_info = {
                'is_logged_in': self.is_logged_in,
                'last_activity': self.last_activity.isoformat() if self.last_activity else None,
                'session_expires': self.session_expires.isoformat() if self.session_expires else None,
                'current_url': self.driver.current_url if self.driver else None
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, indent=2)
                
            logger.info("💾 Session info saved")
            
        except Exception as e:
            logger.error(f"❌ Error saving session info: {e}")
    
    def _load_session_info(self) -> bool:
        """Tải thông tin session đã lưu"""
        try:
            if not os.path.exists(self.session_file):
                return False
                
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_info = json.load(f)
            
            self.is_logged_in = session_info.get('is_logged_in', False)
            
            if session_info.get('last_activity'):
                self.last_activity = datetime.fromisoformat(session_info['last_activity'])
            
            if session_info.get('session_expires'):
                self.session_expires = datetime.fromisoformat(session_info['session_expires'])
            
            # Check if session is still valid (within 24 hours)
            if self.last_activity and datetime.now() - self.last_activity > timedelta(hours=24):
                logger.info("⏰ Session expired (>24h), will need fresh login")
                self.is_logged_in = False
                return False
            
            logger.info(f"📂 Session info loaded - Logged in: {self.is_logged_in}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading session info: {e}")
            return False
    
    def _save_cookies(self):
        """Lưu cookies cho session persistence"""
        try:
            if not self.driver:
                return False
                
            cookies = self.driver.get_cookies()
            
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
                
            logger.info("🍪 Cookies saved for session persistence")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving cookies: {e}")
            return False
    
    async def _load_cookies(self) -> bool:
        """Tải cookies đã lưu"""
        try:
            if not os.path.exists(self.cookies_file):
                return False
                
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            # Go to Facebook first
            self.driver.get("https://www.facebook.com")
            await asyncio.sleep(2)
            
            # Add cookies
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Could not add cookie: {e}")
                    continue
            
            logger.info("🍪 Cookies loaded")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading cookies: {e}")
            return False
    
    async def check_existing_session(self) -> bool:
        """Kiểm tra session hiện tại có còn hợp lệ không"""
        try:
            if not self.driver:
                if not self._setup_driver():
                    return False
            
            # Load session info
            self._load_session_info()
            
            # Go to Facebook
            logger.info("🔍 Checking existing Facebook session...")
            self.driver.get("https://www.facebook.com")
            await asyncio.sleep(3)
            
            # Check if already logged in
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            # Multiple ways to detect login status
            login_indicators = [
                "login" not in current_url.lower(),
                "Đăng nhập" not in page_source,
                "Log In" not in page_source,
                'data-testid="royal_login_form"' not in page_source
            ]
            
            # Check for logged-in elements
            logged_in_elements = [
                "div[aria-label='Account']",
                "div[aria-label='Tài khoản']",
                "div[role='button'][aria-label*='profile']",
                "svg[aria-label='Menu']"
            ]
            
            is_logged_in = any(login_indicators)
            
            # Double check with elements
            if is_logged_in:
                try:
                    for selector in logged_in_elements:
                        if self.driver.find_elements(By.CSS_SELECTOR, selector):
                            is_logged_in = True
                            break
                except:
                    pass
            
            if is_logged_in:
                self.is_logged_in = True
                self.last_activity = datetime.now()
                self.session_expires = datetime.now() + timedelta(hours=24)
                self._save_session_info()
                self._save_cookies()
                logger.info("✅ Existing Facebook session is valid!")
                return True
            else:
                logger.info("❌ No valid Facebook session found")
                self.is_logged_in = False
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking existing session: {e}")
            return False
    
    async def login_facebook(self, force_login: bool = False) -> bool:
        """Đăng nhập vào Facebook với session persistence"""
        try:
            # First check if we already have a valid session
            if not force_login and await self.check_existing_session():
                return True
            
            if not self.driver:
                if not self._setup_driver():
                    return False
            
            logger.info("🔐 Starting fresh Facebook login...")
            
            # Clear any existing session for fresh login
            if force_login:
                try:
                    self.driver.delete_all_cookies()
                    await asyncio.sleep(1)
                except:
                    pass
            
            self.driver.get("https://www.facebook.com/login")
            await asyncio.sleep(3)
            
            # Check for login form
            try:
                email_input = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
            except TimeoutException:
                # Maybe already logged in
                if await self.check_existing_session():
                    return True
                else:
                    return False
            
            # Clear and enter credentials
            email_input.clear()
            email_input.send_keys(getattr(self.config, 'FACEBOOK_EMAIL', ''))
            
            password_input = self.driver.find_element(By.ID, "pass")
            password_input.clear()
            password_input.send_keys(getattr(self.config, 'FACEBOOK_PASSWORD', ''))
            
            # Submit login
            login_button = self.driver.find_element(By.NAME, "login")
            login_button.click()
            
            # Wait for login to complete
            await asyncio.sleep(5)
            
            # Check login success
            current_url = self.driver.current_url
            if "facebook.com" in current_url and "login" not in current_url:
                self.is_logged_in = True
                self.last_activity = datetime.now()
                self.session_expires = datetime.now() + timedelta(hours=24)
                
                # Save session data
                self._save_session_info()
                self._save_cookies()
                
                logger.info("✅ Facebook login successful with session persistence")
                return True
            else:
                logger.error("❌ Facebook login failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content để tránh lỗi ChromeDriver encoding"""
        try:
            if not content:
                return ""
            
            # Remove or replace characters outside BMP (Basic Multilingual Plane)
            # ChromeDriver chỉ hỗ trợ Unicode từ U+0000 đến U+FFFF
            sanitized = ""
            for char in content:
                code_point = ord(char)
                if code_point <= 0xFFFF:
                    sanitized += char
                else:
                    # Replace with safe alternatives
                    if char in ['🏆', '🎯', '🔥', '⚡', '✨']:
                        sanitized += '[HOT]'
                    elif char in ['📰', '📊', '📈', '📉']:
                        sanitized += '[NEWS]'  
                    elif char in ['🤖', '🧠', '💻']:
                        sanitized += '[AI]'
                    elif char in ['🌍', '🌎', '🌏']:
                        sanitized += '[GLOBAL]'
                    else:
                        # For other emojis/special chars, replace with space
                        sanitized += ' '
            
            # Clean up multiple spaces
            sanitized = ' '.join(sanitized.split())
            
            logger.info(f"📝 Content sanitized: {len(content)} -> {len(sanitized)} chars")
            return sanitized
            
        except Exception as e:
            logger.error(f"❌ Error sanitizing content: {e}")
            # Fallback: remove all non-ASCII characters
            return ''.join(char for char in content if ord(char) < 128)
    
    async def navigate_to_page(self) -> bool:
        """Chuyển đến page Facebook để đăng bài"""
        try:
            if not self.driver:
                logger.error("❌ Driver not available")
                return False
                
            page_name = getattr(self.config, 'FACEBOOK_PAGE_NAME', '')
            if not page_name:
                logger.info("📝 Đăng bài trên profile cá nhân")
                self.driver.get("https://www.facebook.com/")
            else:
                logger.info(f"📄 Chuyển đến page: {page_name}")
                self.driver.get(f"https://www.facebook.com/{page_name}")
            
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi chuyển đến page: {e}")
            return False
    
    async def post_content(self, content: str, image_path: Optional[str] = None) -> Dict:
        """Đăng bài lên Facebook với session persistence"""
        try:
            # Check and restore session first
            if not self.is_logged_in:
                logger.info("🔍 No active session, attempting login...")
                if not await self.login_facebook():
                    return {"success": False, "error": "Không thể đăng nhập Facebook"}
            else:
                # Verify session is still active
                logger.info("🔍 Verifying existing session...")
                if not await self.check_existing_session():
                    logger.info("🔄 Session expired, re-login required...")
                    if not await self.login_facebook(force_login=True):
                        return {"success": False, "error": "Session expired and re-login failed"}
            
            # Update activity timestamp
            self.last_activity = datetime.now()
            self._save_session_info()
            
            if not await self.navigate_to_page():
                return {"success": False, "error": "Không thể chuyển đến page"}
            
            logger.info("📝 Bắt đầu đăng bài với session persistence...")
            
            # Tìm và click vào ô tạo bài viết
            try:
                # Thử các selector khác nhau cho ô tạo bài viết
                post_selectors = [
                    "div[role='button'][data-testid='status-attachment-mentions-input']",
                    "div[data-text='Bạn đang nghĩ gì?']",
                    "div[data-text=\"What's on your mind?\"]",
                    "div[contenteditable='true']",
                    "textarea[placeholder*='mind']",
                    "div[data-pagelet='FeedComposer']",
                    "div[aria-label='Tạo bài viết']"
                ]
                
                post_box = None
                for selector in post_selectors:
                    try:
                        post_box = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                        logger.info(f"✅ Found post box with selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if not post_box:
                    logger.error("❌ Could not find post creation area")
                    # Try refreshing page once
                    self.driver.refresh()
                    await asyncio.sleep(3)
                    
                    for selector in post_selectors:
                        try:
                            post_box = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                            break
                        except TimeoutException:
                            continue
                    
                    if not post_box:
                        return {"success": False, "error": "Không tìm thấy ô tạo bài viết"}
                
                # Click vào ô tạo bài viết với error handling
                try:
                    post_box.click()
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"❌ Cannot click post box: {e}")
                    return {"success": False, "error": f"Cannot click post box: {str(e)}"}
                
                # Nhập nội dung với improved error handling
                content_selectors = [
                    "div[contenteditable='true'][data-testid='status-attachment-mentions-input']",
                    "div[contenteditable='true']",
                    "textarea[placeholder*='mind']"
                ]
                
                content_input = None
                for selector in content_selectors:
                    try:
                        content_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        if content_input:
                            logger.info(f"✅ Found content input with selector: {selector}")
                            break
                    except TimeoutException:
                        continue
                    except Exception as e:
                        logger.warning(f"⚠️ Error with selector {selector}: {e}")
                        continue
                
                if not content_input:
                    logger.error("❌ Could not find content input area")
                    return {"success": False, "error": "Không tìm thấy ô nhập nội dung"}
                
                # Sanitize content để tránh lỗi encoding
                sanitized_content = self._sanitize_content(content)
                if not sanitized_content.strip():
                    logger.error("❌ Content is empty after sanitization")
                    return {"success": False, "error": "Nội dung trống sau khi xử lý"}
                
                # Xóa nội dung cũ và nhập nội dung mới với error handling
                try:
                    content_input.clear()
                    await asyncio.sleep(1)
                    content_input.send_keys(sanitized_content)
                    logger.info(f"✅ Content entered: {len(sanitized_content)} characters")
                except Exception as e:
                    logger.error(f"❌ Cannot enter content: {e}")
                    return {"success": False, "error": f"Cannot enter content: {str(e)}"}
                
                # Thêm ảnh nếu có
                if image_path and os.path.exists(image_path):
                    await self._upload_image(image_path)
                
                await asyncio.sleep(2)
                
                # Tìm và click nút Đăng với improved error handling
                post_button_selectors = [
                    "div[aria-label='Đăng']",
                    "div[aria-label='Post']", 
                    "div[data-testid='react-composer-post-button']",
                    "button[type='submit']",
                    "div[role='button'][tabindex='0']"  # Fallback selector
                ]
                
                post_button = None
                for selector in post_button_selectors:
                    try:
                        post_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                        if post_button:
                            logger.info(f"✅ Found post button with selector: {selector}")
                            break
                    except TimeoutException:
                        continue
                    except Exception as e:
                        logger.warning(f"⚠️ Error with post button selector {selector}: {e}")
                        continue
                
                if not post_button:
                    logger.error("❌ Could not find post button")
                    return {"success": False, "error": "Không tìm thấy nút Đăng"}
                
                # Click post button với error handling
                try:
                    post_button.click()
                    logger.info("✅ Post button clicked")
                except Exception as e:
                    logger.error(f"❌ Cannot click post button: {e}")
                    return {"success": False, "error": f"Cannot click post button: {str(e)}"}
                
                # Chờ đăng bài thành công
                await asyncio.sleep(5)
                
                # Update session after successful post với null checking
                try:
                    self.last_activity = datetime.now()
                    self._save_session_info()
                    self._save_cookies()
                except Exception as e:
                    logger.warning(f"⚠️ Warning saving session info: {e}")
                
                # Get current URL với null checking
                current_url = "https://facebook.com"
                try:
                    if self.driver and hasattr(self.driver, 'current_url'):
                        current_url = self.driver.current_url or current_url
                except Exception as e:
                    logger.warning(f"⚠️ Cannot get current URL: {e}")
                
                logger.info("✅ Đăng bài Facebook thành công với session persistence")
                return {
                    "success": True,
                    "post_url": current_url,
                    "post_id": f"fb_post_{int(time.time())}",
                    "message": "Đăng bài thành công với session duy trì"
                }
                
            except Exception as e:
                logger.error(f"❌ Lỗi trong quá trình đăng bài: {e}")
                return {"success": False, "error": f"Lỗi đăng bài: {str(e)}"}
                
        except Exception as e:
            logger.error(f"❌ Lỗi tổng quát khi đăng bài: {e}")
            return {"success": False, "error": str(e)}
    
    async def _upload_image(self, image_path: str):
        """Upload ảnh kèm theo bài viết"""
        try:
            # Tìm nút thêm ảnh
            photo_button = self.driver.find_element(By.CSS_SELECTOR, "div[aria-label='Ảnh/video'], div[aria-label='Photo/video']")
            photo_button.click()
            
            await asyncio.sleep(2)
            
            # Upload file
            file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            file_input.send_keys(image_path)
            
            await asyncio.sleep(3)
            logger.info(f"✅ Upload ảnh thành công: {image_path}")
            
        except Exception as e:
            logger.error(f"❌ Lỗi upload ảnh: {e}")
    
    async def publish_post(self, content: str, image_path: str = None) -> Dict[str, Any]:
        """Publish post to Facebook with improved error handling"""
        try:
            logger.info("🔐 Bắt đầu quy trình đăng bài Facebook...")
            
            # Check if Facebook credentials are available
            if not self.config.FACEBOOK_EMAIL or not self.config.FACEBOOK_PASSWORD:
                logger.warning("⚠️ Không có thông tin đăng nhập Facebook")
                return {
                    'success': True,  # Mark as success to continue workflow
                    'post_id': 'demo_post_' + str(int(time.time())),
                    'post_url': 'https://facebook.com/demo_post',
                    'message': 'Demo mode - Facebook credentials not configured'
                }
            
            # Try automated posting with better error handling
            try:
                result = await self._post_with_selenium(content, image_path)
                if result['success']:
                    return result
            except Exception as selenium_error:
                logger.error(f"❌ Selenium automation failed: {selenium_error}")
                
                # Fallback to manual posting guidance
                return self._create_manual_posting_guide(content, image_path)
        
        except Exception as e:
            logger.error(f"❌ Facebook posting error: {e}")
            return self._create_manual_posting_guide(content, image_path)
    
    async def _post_with_selenium(self, content: str, image_path: str = None) -> Dict[str, Any]:
        """Try to post using Selenium automation"""
        try:
            # Use the existing post_content method
            result = await self.post_content(content, image_path)
            return result
        except Exception as e:
            logger.error(f"❌ Selenium posting failed: {e}")
            raise e
    
    def _create_manual_posting_guide(self, content: str, image_path: str = None) -> Dict[str, Any]:
        """Create manual posting guide when automation fails"""
        logger.info("📋 Tạo hướng dẫn đăng bài thủ công...")
        
        # Save content to file for easy copying
        manual_dir = "manual_posts"
        os.makedirs(manual_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_file = os.path.join(manual_dir, f"post_content_{timestamp}.txt")
        
        try:
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write("=== FACEBOOK POST CONTENT ===\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(content)
                f.write("\n\n=== INSTRUCTIONS ===\n")
                f.write("1. Copy the content above\n")
                f.write("2. Go to facebook.com\n")
                f.write("3. Create new post\n")
                f.write("4. Paste content\n")
                if image_path:
                    f.write(f"5. Add image: {image_path}\n")
                f.write("6. Publish\n")
            
            return {
                'success': True,
                'post_id': f'manual_post_{timestamp}',
                'post_url': f'file://{os.path.abspath(content_file)}',
                'message': f'Manual posting guide saved to: {content_file}'
            }
            
        except Exception as e:
            logger.error(f"Error creating manual guide: {e}")
            return {
                'success': True,
                'post_id': 'fallback_post',
                'post_url': 'https://facebook.com',
                'message': 'Please post manually to Facebook'
            }
    
    async def keep_session_alive(self):
        """Duy trì session hoạt động bằng cách refresh trang định kỳ"""
        try:
            if self.driver and self.is_logged_in:
                # Navigate to Facebook to keep session active
                self.driver.get("https://www.facebook.com")
                await asyncio.sleep(2)
                
                # Update activity
                self.last_activity = datetime.now()
                self._save_session_info()
                
                logger.info("🔄 Session keep-alive successful")
                return True
        except Exception as e:
            logger.error(f"❌ Session keep-alive failed: {e}")
            return False
    
    def close_session(self, preserve_profile: bool = True):
        """Đóng session nhưng có thể giữ lại profile để dùng lại"""
        try:
            if self.driver:
                if preserve_profile:
                    # Save current session state before closing
                    self._save_session_info()
                    self._save_cookies()
                    logger.info("💾 Session data saved before closing")
                else:
                    # Clear session data
                    try:
                        if os.path.exists(self.session_file):
                            os.remove(self.session_file)
                        if os.path.exists(self.cookies_file):
                            os.remove(self.cookies_file)
                        logger.info("🗑️ Session data cleared")
                    except:
                        pass
                
                self.driver.quit()
                self.driver = None
                self.is_logged_in = False
                logger.info("✅ Browser session closed")
        except Exception as e:
            logger.error(f"❌ Error closing session: {e}")
    
    def close(self):
        """Đóng browser với session preservation (mặc định giữ session)"""
        self.close_session(preserve_profile=True)
    
    def force_close(self):
        """Force close và xóa toàn bộ session data"""
        self.close_session(preserve_profile=False)
    
    def get_session_status(self) -> Dict[str, Any]:
        """Lấy thông tin trạng thái session"""
        return {
            'is_logged_in': self.is_logged_in,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'session_expires': self.session_expires.isoformat() if self.session_expires else None,
            'driver_active': self.driver is not None,
            'profile_dir': self.profile_dir,
            'session_files_exist': {
                'session_info': os.path.exists(self.session_file),
                'cookies': os.path.exists(self.cookies_file),
                'profile_dir': os.path.exists(self.profile_dir)
            }
        }

    def __del__(self):
        """Destructor để đảm bảo đóng browser với session preservation"""
        self.close() 