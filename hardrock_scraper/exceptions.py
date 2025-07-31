"""Custom exceptions for HardRock scraper"""


class ScraperError(Exception):
    """Base exception for scraper errors"""
    pass


class ParseError(ScraperError):
    """Exception raised when HTML parsing fails"""
    pass


class ChromeError(ScraperError):
    """Exception raised when Chrome driver encounters issues"""
    pass


class RateLimitError(ScraperError):
    """Exception raised when rate limiting is detected"""
    pass


class DataNotFoundError(ParseError):
    """Exception raised when expected data is not found in HTML"""
    pass