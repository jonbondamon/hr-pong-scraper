"""Chrome driver management with undetectable settings"""

import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

from .exceptions import ChromeError


class ChromeManager:
    """Manages Chrome WebDriver with stealth settings for scraping"""
    
    def __init__(self, headless: bool = True, user_agent: Optional[str] = None):
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless
        self.user_agent = user_agent or self._get_default_user_agent()
        self.logger = logging.getLogger(__name__)
        
    def _get_default_user_agent(self) -> str:
        """Get a realistic user agent string"""
        return ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    def start_driver(self, max_retries: int = 3) -> webdriver.Chrome:
        """Initialize and return Chrome driver with stealth settings and retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Starting Chrome driver (attempt {attempt + 1}/{max_retries})")
                
                if UNDETECTED_AVAILABLE:
                    self.driver = self._create_undetected_driver()
                else:
                    self.driver = self._create_standard_driver()
                    
                self._configure_driver()
                self.logger.info("Chrome driver started successfully")
                return self.driver
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Chrome driver start attempt {attempt + 1} failed: {e}")
                
                # Clean up any partial driver
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                
                # Wait before retry (except on last attempt)
                if attempt < max_retries - 1:
                    import time
                    time.sleep(3)
        
        # All attempts failed
        raise ChromeError(f"Failed to start Chrome driver after {max_retries} attempts: {last_error}")
    
    def _create_undetected_driver(self) -> webdriver.Chrome:
        """Create undetected Chrome driver"""
        options = uc.ChromeOptions()
        
        # Container-friendly settings  
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Memory and performance optimizations for containers
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # Network and loading optimizations
        options.add_argument('--aggressive-cache-discard')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-extensions')
        
        # JavaScript and rendering optimizations
        options.add_argument('--disable-hang-monitor')
        options.add_argument('--disable-prompt-on-repost')
        options.add_argument('--disable-web-security')  # Only for scraping
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Headless mode
        if self.headless:
            options.add_argument('--headless=new')
        
        # Performance optimizations
        options.add_argument('--disable-images')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # Memory optimizations
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # Remove problematic experimental options for container compatibility
        try:
            return uc.Chrome(options=options, version_main=None)
        except Exception as e:
            self.logger.warning(f"Undetected Chrome failed, falling back to standard: {e}")
            return self._create_standard_driver()
    
    def _create_standard_driver(self) -> webdriver.Chrome:
        """Create standard Chrome driver with stealth settings"""
        options = Options()
        
        # Basic stealth settings
        options.add_argument(f'--user-agent={self.user_agent}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Performance optimizations
        options.add_argument('--disable-images')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        return webdriver.Chrome(options=options)
    
    def _configure_driver(self):
        """Configure driver with additional stealth settings"""
        if not self.driver:
            return
            
        # Remove webdriver property
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        # Set realistic viewport
        self.driver.set_window_size(1920, 1080)
        
        # Set timeouts
        self.driver.implicitly_wait(10)
        self.driver.set_page_load_timeout(30)
    
    def get_page(self, url: str, wait_for_element: Optional[str] = None, 
                 timeout: int = 20) -> str:
        """Navigate to page and return HTML content"""
        if not self.driver:
            raise ChromeError("Driver not initialized. Call start_driver() first.")
        
        try:
            self.logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for specific element if provided
            if wait_for_element:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                )
            else:
                # Default wait for page load
                time.sleep(3)
            
            # Wait for JavaScript to render (if needed)
            self._wait_for_js_load()
            
            return self.driver.page_source
            
        except TimeoutException:
            raise ChromeError(f"Timeout waiting for page to load: {url}")
        except WebDriverException as e:
            raise ChromeError(f"WebDriver error: {e}")
    
    def _wait_for_js_load(self, timeout: int = 15):
        """Wait for JavaScript to finish loading and dynamic content to appear"""
        try:
            # Step 1: Wait for document ready
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Step 2: Wait for HardRock specific content to load
            self._wait_for_hardrock_content(timeout)
            
        except TimeoutException:
            self.logger.warning("JavaScript loading timeout - proceeding anyway")
    
    def _wait_for_hardrock_content(self, timeout: int = 15):
        """Wait specifically for HardRock betting content to load"""
        try:
            # Wait for match containers to appear
            self.logger.debug("Waiting for match containers...")
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".hr-market-view, [class*='event']"))
            )
            
            # Additional wait for odds to load (they load after containers)
            self.logger.debug("Waiting for odds content...")
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".selection-odds, .selection-container"))
                )
            except TimeoutException:
                self.logger.debug("Odds containers not found - may be no betting available")
            
            # Wait a bit more for any final AJAX calls
            time.sleep(2)
            
        except TimeoutException:
            self.logger.warning("HardRock content loading timeout - checking for fallback selectors")
            # Check if we have any content at all
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                self.logger.error("No body content found - page may have failed to load")
    
    def refresh_page(self) -> str:
        """Refresh current page and return HTML"""
        if not self.driver:
            raise ChromeError("Driver not initialized")
        
        try:
            self.driver.refresh()
            self._wait_for_js_load()
            return self.driver.page_source
        except WebDriverException as e:
            raise ChromeError(f"Failed to refresh page: {e}")
    
    def execute_script(self, script: str):
        """Execute JavaScript in the browser"""
        if not self.driver:
            raise ChromeError("Driver not initialized")
        
        try:
            return self.driver.execute_script(script)
        except WebDriverException as e:
            raise ChromeError(f"Failed to execute script: {e}")
    
    def is_alive(self) -> bool:
        """Check if driver is still responsive"""
        if not self.driver:
            return False
        
        try:
            self.driver.current_url
            return True
        except:
            return False
    
    def restart_driver(self) -> webdriver.Chrome:
        """Restart the Chrome driver"""
        self.logger.info("Restarting Chrome driver")
        self.quit_driver()
        return self.start_driver()
    
    def quit_driver(self):
        """Safely quit the Chrome driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass  # Ignore errors during cleanup
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry"""
        self.start_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.quit_driver()