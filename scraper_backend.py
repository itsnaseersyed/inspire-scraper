"""
Backend scraper module that can be imported and used by the web interface
Modified version of scrap_production.py with callback support
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import logging
import time
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import all the classes and functions from scrap_production
# We'll use the same Config, setup_logging, and utilities

class Config:
    """Configuration settings for the scraper."""
    BASE_URL = "https://www.inspireawards-dst.gov.in/UserP/Contact-detailsAtPublicDomain.aspx"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 1
    RATE_LIMIT_DELAY = 0.5  # Faster for web interface
    OUTPUT_DIR = Path("output")
    CHECKPOINT_FILE = OUTPUT_DIR / "checkpoint.json"
    LOG_FILE = OUTPUT_DIR / "scraper.log"
    BATCH_SIZE = 50


def setup_logging(log_file: Path) -> logging.Logger:
    """Configure logging"""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("INSPIRE_Scraper")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def create_session(config: Config) -> requests.Session:
    """Create a requests session with retry logic"""
    session = requests.Session()
    session.headers.update(config.HEADERS)
    
    retry_strategy = Retry(
        total=config.MAX_RETRIES,
        backoff_factor=config.BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def parse_delta(text: str) -> Dict[str, str]:
    """Parse ASP.NET AJAX delta response"""
    def extract(name: str) -> str:
        pattern = rf'\|(\d+)\|hiddenField\|{name}\|'
        match = re.search(pattern, text)
        if match:
            length = int(match.group(1))
            start_pos = match.end()
            value = text[start_pos:start_pos + length]
            return value
        return ""
    
    return {
        "viewstate": extract("__VIEWSTATE"),
        "eventvalidation": extract("__EVENTVALIDATION"),
        "viewstategen": extract("__VIEWSTATEGENERATOR")
    }


def extract_dropdown_from_delta(text: str, dropdown_id: str) -> Dict[str, str]:
    """Extract dropdown options from ASP.NET AJAX delta response"""
    soup = BeautifulSoup(text, "lxml")
    dropdown = soup.find("select", {"id": dropdown_id})
    
    if not dropdown:
        return {}
    
    options = {}
    for option in dropdown.find_all("option"):
        value = option.get("value", "")
        label = option.text.strip()
        if value and value != "0" and label:
            options[value] = label
    
    return options


def extract_viewstate_from_html(soup: BeautifulSoup) -> Tuple[str, str, str]:
    """Extract ASP.NET view state parameters from HTML"""
    try:
        viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
        eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]
        viewstategen = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})["value"]
        return viewstate, eventvalidation, viewstategen
    except (TypeError, KeyError) as e:
        raise ValueError(f"Failed to extract view state parameters: {e}")


class InspireScraper:
    """Main scraper class with callback support for web interface"""
    
    def __init__(self, config: Config, logger: logging.Logger, callback=None):
        self.config = config
        self.logger = logger
        self.session = create_session(config)
        self.data: List[Dict] = []
        self.callback = callback
        
        self.viewstate = ""
        self.eventvalidation = ""
        self.viewstategen = ""
    
    def make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make an HTTP request with error handling"""
        kwargs.setdefault('timeout', self.config.REQUEST_TIMEOUT)
        
        try:
            time.sleep(self.config.RATE_LIMIT_DELAY)
            
            if method.upper() == 'GET':
                response = self.session.get(url, **kwargs)
            else:
                response = self.session.post(url, **kwargs)
            
            response.raise_for_status()
            return response
            
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return None
    
    def initialize_page(self) -> bool:
        """Load the initial page"""
        response = self.make_request('GET', self.config.BASE_URL)
        if not response:
            return False
        
        try:
            soup = BeautifulSoup(response.text, "lxml")
            self.viewstate, self.eventvalidation, self.viewstategen = extract_viewstate_from_html(soup)
            return True
        except ValueError:
            return False
    
    def select_school_mode(self) -> bool:
        """Select 'School Details' radio button"""
        payload = {
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$rblSelect$2",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstategen,
            "__EVENTVALIDATION": self.eventvalidation,
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$rblSelect": "2"
        }
        
        response = self.make_request('POST', self.config.BASE_URL, data=payload)
        if not response:
            return False
        
        try:
            delta = parse_delta(response.text)
            self.viewstate = delta["viewstate"]
            self.eventvalidation = delta["eventvalidation"]
            self.viewstategen = delta["viewstategen"]
            return True
        except:
            return False
    
    def select_state(self, state_id: str) -> Optional[Dict[str, str]]:
        """Select a state and get districts"""
        payload = {
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlState",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstategen,
            "__EVENTVALIDATION": self.eventvalidation,
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$rblSelect": "2",
            "ctl00$ContentPlaceHolder1$ddlState": state_id
        }
        
        response = self.make_request('POST', self.config.BASE_URL, data=payload)
        if not response:
            return None
        
        try:
            delta = parse_delta(response.text)
            self.viewstate = delta["viewstate"]
            self.eventvalidation = delta["eventvalidation"]
            self.viewstategen = delta["viewstategen"]
            
            districts = extract_dropdown_from_delta(response.text, "ctl00_ContentPlaceHolder1_ddlDist")
            return districts if districts else {}
        except:
            return None
    
    def select_district(self, state_id: str, dist_id: str) -> Optional[Dict[str, str]]:
        """Select a district and get schools"""
        payload = {
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlDist",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstategen,
            "__EVENTVALIDATION": self.eventvalidation,
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$rblSelect": "2",
            "ctl00$ContentPlaceHolder1$ddlState": state_id,
            "ctl00$ContentPlaceHolder1$ddlDist": dist_id
        }
        
        response = self.make_request('POST', self.config.BASE_URL, data=payload)
        if not response:
            return None
        
        try:
            delta = parse_delta(response.text)
            self.viewstate = delta["viewstate"]
            self.eventvalidation = delta["eventvalidation"]
            self.viewstategen = delta["viewstategen"]
            
            schools = extract_dropdown_from_delta(response.text, "ctl00_ContentPlaceHolder1_ddlSchool")
            return schools if schools else {}
        except:
            return None
    
    def scrape_school_contacts(self, state_id: str, state_name: str, dist_id: str, 
                               dist_name: str, school_id: str, school_name: str) -> int:
        """Scrape contact details for a specific school (legacy - stores internally)"""
        contacts = self.scrape_school_contacts_return(state_id, state_name, dist_id, dist_name, school_id, school_name)
        self.data.extend(contacts)
        return len(contacts)
    
    def scrape_school_contacts_return(self, state_id: str, state_name: str, dist_id: str, 
                                      dist_name: str, school_id: str, school_name: str) -> List[Dict]:
        """Scrape contact details and return them (for district-wise saving)"""
        payload = {
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$btnSubmit",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstategen,
            "__EVENTVALIDATION": self.eventvalidation,
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$rblSelect": "2",
            "ctl00$ContentPlaceHolder1$ddlState": state_id,
            "ctl00$ContentPlaceHolder1$ddlDist": dist_id,
            "ctl00$ContentPlaceHolder1$ddlSchool": school_id
        }
        
        response = self.make_request('POST', self.config.BASE_URL, data=payload)
        if not response:
            return []
        
        try:
            soup = BeautifulSoup(response.text, "lxml")
            table = soup.find("table", id="ctl00_ContentPlaceHolder1_grdContactDtl")
            
            if not table:
                return []
            
            contacts = []
            rows = table.select("tr")[1:]
            
            for row in rows:
                cols = [cell.text.strip() for cell in row.find_all("td")]
                
                if len(cols) >= 6:
                    contact_data = {
                        "State": state_name,
                        "District": dist_name,
                        "School": cols[1],
                        "Name": cols[2],
                        "Mobile": cols[3],
                        "Email": cols[4],
                        "Application_Number": cols[5]
                    }
                    
                    if contact_data["Name"] or contact_data["Mobile"] or contact_data["Email"]:
                        contacts.append(contact_data)
            
            return contacts
            
        except Exception as e:
            self.logger.error(f"Failed to scrape school {school_name}: {e}")
            return []
    
    def save_data_to_file(self, filename: Path) -> None:
        """Save scraped data to Excel file"""
        if not self.data:
            return
        
        try:
            df = pd.DataFrame(self.data)
            filename.parent.mkdir(parents=True, exist_ok=True)
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Contact Details')
                worksheet = writer.sheets['Contact Details']
                for idx, col in enumerate(df.columns):
                    max_length = max(df[col].astype(str).apply(len).max(), len(col))
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            self.logger.info(f"Data saved: {filename} ({len(df)} records)")
            
        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")
    
    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            self.session.close()
        except:
            pass
