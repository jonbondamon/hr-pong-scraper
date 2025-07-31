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
    
    def start_driver(self) -> webdriver.Chrome:
        """Initialize and return Chrome driver with stealth settings"""
        try:
            if UNDETECTED_AVAILABLE:
                self.driver = self._create_undetected_driver()
            else:
                self.driver = self._create_standard_driver()
                
            self._configure_driver()
            return self.driver
            
        except Exception as e:
            raise ChromeError(f"Failed to start Chrome driver: {e}")
    
    def _create_undetected_driver(self) -> webdriver.Chrome:
        """Create undetected Chrome driver"""
        options = uc.ChromeOptions()
        
        # Stealth settings
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Performance optimizations
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')  # Remove if JS is needed for data loading
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-extensions')
        
        # Memory optimizations
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        return uc.Chrome(options=options, version_main=None)
    
    def _create_standard_driver(self) -> webdriver.Chrome:
        """Create standard Chrome driver with stealth settings"""
        options = Options()
        
        # Basic stealth settings
        options.add_argument(f'--user-agent={self.user_agent}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Performance optimizations
        options.add_argument('--disable-images')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-extensions')
        
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
    
    def _wait_for_js_load(self, timeout: int = 10):
        """Wait for JavaScript to finish loading"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            self.logger.warning("JavaScript loading timeout - proceeding anyway")
    
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