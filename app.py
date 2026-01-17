"""
Flask Web Application for INSPIRE Contact Details Scraper
Provides a web interface to select states and scrape school contact details
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import threading
import json
import os
from pathlib import Path
from datetime import datetime
from scraper_backend import InspireScraper, Config, setup_logging

app = Flask(__name__)
CORS(app)

# Global variables to track scraping status
scraping_status = {
    "is_running": False,
    "current_state": "",
    "current_district": "",
    "current_school": "",
    "total_available": 0,
    "total_records": 0,
    "progress": 0,
    "should_stop": False,
    "message": "Ready to scrape",
    "error": None
}

# Available states (will be populated dynamically)
STATES = {
    "1": "Andaman And Nicobar",
    "2": "Andhra Pradesh",
    "3": "Arunachal Pradesh",
    "4": "Assam",
    "5": "Bihar",
    "6": "Chandigarh",
    "7": "Chhattisgarh",
    "42": "Dadra And Nagar Haveli And Daman And Diu",
    "10": "Delhi",
    "11": "Goa",
    "12": "Gujarat",
    "13": "Haryana",
    "14": "Himachal Pradesh",
    "15": "Jammu And Kashmir",
    "16": "Jharkhand",
    "17": "Karnataka",
    "36": "Kendriya Vidyalaya Sangathan",
    "18": "Kerala",
    "40": "Ladakh",
    "19": "Lakshadweep",
    "20": "Madhya Pradesh",
    "21": "Maharashtra",
    "22": "Manipur",
    "23": "Meghalaya",
    "24": "Mizoram",
    "25": "Nagaland",
    "37": "Navodaya Vidyalaya Samiti",
    "26": "Odisha",
    "27": "Puducherry",
    "28": "Punjab",
    "29": "Rajasthan",
    "38": "Sainik Schools Society",
    "30": "Sikkim",
    "31": "Tamil Nadu",
    "39": "Telangana",
    "32": "Tripura",
    "33": "Uttar Pradesh",
    "34": "Uttarakhand",
    "35": "West Bengal"
}


class StatusCallback:
    """Callback class to update scraping status"""
    
    def __init__(self):
        self.total_records = 0
    
    def update_state(self, state_name):
        scraping_status["current_state"] = state_name
        scraping_status["message"] = f"Processing state: {state_name}"
    
    def update_district(self, district_name):
        scraping_status["current_district"] = district_name
        scraping_status["message"] = f"Processing district: {district_name}"
    
    def update_school(self, school_name, current, total):
        scraping_status["current_school"] = school_name
        scraping_status["total_available"] = total
        scraping_status["progress"] = int((current / total) * 100) if total > 0 else 0
        scraping_status["message"] = f"Scraping school {current}/{total}: {school_name}"
    
    def update_records(self, count):
        self.total_records = count
        scraping_status["total_records"] = count
    
    def set_error(self, error_msg):
        scraping_status["error"] = error_msg
        scraping_status["message"] = f"Error: {error_msg}"


def run_scraper(state_id, selected_districts, callback):
    """Run the scraper in a background thread"""
    global scraping_status
    
    try:
        scraping_status["is_running"] = True
        scraping_status["error"] = None
        scraping_status["total_records"] = 0
        
        # Initialize configuration and logger
        config = Config()
        logger = setup_logging(config.LOG_FILE)
        
        # Create scraper instance
        scraper = InspireScraper(config, logger, callback)
        
        # Initialize page
        if not scraper.initialize_page():
            callback.set_error("Failed to initialize scraper")
            return
        
        if not scraper.select_school_mode():
            callback.set_error("Failed to select school mode")
            return
        
        # Get state name
        state_name = STATES.get(state_id, f"State_{state_id}")
        callback.update_state(state_name)
        
        # Get all districts for this state
        all_districts = scraper.select_state(state_id)
        if not all_districts:
            callback.set_error(f"Failed to get districts for {state_name}")
            return
        
        # Filter districts based on selection
        if "all" in selected_districts:
            districts_to_scrape = all_districts
        else:
            districts_to_scrape = {k: v for k, v in all_districts.items() if k in selected_districts}
        
        # Create state folder
        state_folder = config.OUTPUT_DIR / state_name.replace(" ", "_")
        state_folder.mkdir(parents=True, exist_ok=True)
        
        # Track generated files
        created_files = []
        
        # Process each district
        for dist_id, dist_name in districts_to_scrape.items():
            if scraping_status.get("should_stop"):
                break
                
            callback.update_district(dist_name)
            district_data = []  # Store data for this district
            
            # Get schools for this district
            schools = scraper.select_district(state_id, dist_id)
            if not schools:
                logger.error(f"Failed to get schools for {dist_name}")
                continue
            
            # Process each school
            total_schools = len(schools)
            for idx, (school_id, school_name) in enumerate(schools.items(), 1):
                # Check for stop signal
                if scraping_status.get("should_stop"):
                    logger.info("Stop signal received. Finishing school loop.")
                    break

                callback.update_school(school_name, idx, total_schools)
                
                # Scrape contacts and get them
                contacts = scraper.scrape_school_contacts_return(
                    state_id, state_name,
                    dist_id, dist_name,
                    school_id, school_name
                )
                
                if contacts:
                    district_data.extend(contacts)
                    callback.update_records(callback.total_records + len(contacts))
            
            # Save district data to CSV
            if district_data:
                import pandas as pd
                df = pd.DataFrame(district_data)
                csv_filename = state_folder / f"{dist_name.replace(' ', '_').replace('/', '_')}.csv"
                df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                created_files.append(csv_filename)
                logger.info(f"Saved {len(district_data)} records to {csv_filename}")
        
        # Handle Download Logic
        if len(created_files) == 1:
            scraping_status["output_file"] = str(created_files[0])
        elif len(created_files) > 1:
            import shutil
            zip_base = config.OUTPUT_DIR / f"{state_name}_Data"
            shutil.make_archive(str(zip_base), 'zip', state_folder)
            scraping_status["output_file"] = str(zip_base.with_suffix('.zip'))
            
        scraping_status["output_folder"] = str(state_folder)
        scraping_status["message"] = f"✓ Scraping completed! {len(created_files)} files generated."
        
        # Cleanup
        scraper.cleanup()
        
    except Exception as e:
        callback.set_error(str(e))
        import traceback
        logger.error(f"Error in scraper: {traceback.format_exc()}")
    finally:
        scraping_status["is_running"] = False


@app.route('/')
def landing():
    """Render the landing page"""
    return render_template('landing.html')


@app.route('/scraper')
def scraper():
    """Render the scraper dashboard"""
    return render_template('scraper.html', states=STATES)


@app.route('/docs')
def docs():
    """Render the documentation page"""
    return render_template('docs.html')


@app.route('/api/states')
def get_states():
    """Get list of available states"""
    return jsonify(STATES)


@app.route('/api/districts/<state_id>')
def get_districts(state_id):
    """Get districts for a specific state"""
    try:
        # Initialize scraper to fetch districts
        config = Config()
        logger = setup_logging(config.LOG_FILE)
        scraper = InspireScraper(config, logger)
        
        if not scraper.initialize_page():
            return jsonify({"error": "Failed to initialize"}), 500
        
        if not scraper.select_school_mode():
            return jsonify({"error": "Failed to select mode"}), 500
        
        districts = scraper.select_state(state_id)
        scraper.cleanup()
        
        if districts:
            return jsonify(districts)
        else:
            return jsonify({}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/start', methods=['POST'])
def start_scraping():
    """Start scraping for selected state and districts"""
    global scraping_status
    
    if scraping_status["is_running"]:
        return jsonify({"error": "Scraper is already running"}), 400
    
    data = request.get_json()
    state_id = data.get('state_id')
    selected_districts = data.get('districts', [])
    
    if not state_id:
        return jsonify({"error": "No state selected"}), 400
    
    if not selected_districts:
        return jsonify({"error": "No districts selected"}), 400
    
    # Reset status
    scraping_status = {
        "is_running": True,
        "current_state": "",
        "current_district": "",
        "current_school": "",
        "total_available": 0,
        "total_records": 0,
        "progress": 0,
        "should_stop": False,
        "message": "Starting scraper...",
        "error": None,
        "output_file": None
    }
    
    # Start scraping in background thread
    callback = StatusCallback()
    callback.total_records = 0
    thread = threading.Thread(target=run_scraper, args=(state_id, selected_districts, callback))
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "message": "Scraping started"})


@app.route('/api/status')
def get_status():
    """Get current scraping status"""
    return jsonify(scraping_status)


@app.route('/api/stop', methods=['POST'])
def stop_scraping():
    """Signal the scraper to stop gracefully"""
    global scraping_status
    if scraping_status["is_running"]:
        scraping_status["should_stop"] = True
        scraping_status["message"] = "Stopping after current school..."
        return jsonify({"message": "Stopping scraper... Data will be saved."})
    return jsonify({"message": "Scraper is not running"})


@app.route('/api/download')
def download_file():
    """Download the latest scraped data file"""
    output_file = scraping_status.get("output_file")
    if output_file and os.path.exists(output_file):
        return send_file(output_file, as_attachment=True)
    else:
        return jsonify({"error": "No file available for download"}), 404


if __name__ == '__main__':
    # Create output directory if it doesn't exist
    Path("output").mkdir(exist_ok=True)
    
    print("=" * 60)
    print("INSPIRE Contact Details Scraper - Web Interface")
    print("=" * 60)
    print("\nStarting server at http://localhost:5000")
    print("Open this URL in your web browser to use the interface")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    
    # PRODUCTION: Set debug=False for deployment
    # DEVELOPMENT: Set debug=True for development
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
