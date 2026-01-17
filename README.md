# INSPIRE Manak - Sceince Labs and Schools Contact Details Scraper

A production-ready web application for scraping school contact details from the INSPIRE Awards website with an intuitive interface.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Open browser at: **http://localhost:5000**

## 📋 Features

✅ **User-Friendly Web Interface** - No coding required  
✅ **State & District Selection** - Cascading dropdown menus  
✅ **Real-Time Progress Tracking** - See exactly what's being scraped  
✅ **Organized Output** - Data saved as CSV files by state/district  
✅ **Multi-District Support** - Scrape all districts or select specific ones  
✅ **Production Ready** - Error handling, retry logic, and logging  

## 🎯 How to Use

1. **Select a State** from the dropdown
2. **Select Districts** (auto-loads after state selection)
   - Choose "✓ All Districts" for entire state
   - Or Ctrl+Click specific districts
3. **Click "Start Scraping"**
4. **Monitor Progress** in real-time
5. **Find Data** in `output/StateName/DistrictName.csv`

## 📁 Output Structure

```
output/
├── Andhra_Pradesh/
│   ├── Allurisitharamaraju.csv
│   ├── Guntur.csv
│   ├── Krishna.csv
│   └── ...
├── Telangana/
│   ├── Hyderabad.csv
│   └── ...
└── scraper.log
```

## 📊 Data Format

Each CSV contains:
- State
- District
- School
- Contact Name
- Mobile Number
- Email
- Application Number

## 🛠️ Configuration

Edit `scraper_backend.py` → `Config` class to modify:

```python
REQUEST_TIMEOUT = 30        # Request timeout (seconds)
MAX_RETRIES = 3             # Retry attempts
RATE_LIMIT_DELAY = 0.5      # Delay between requests (seconds)
```

## 📦 Project Structure

```
SCRAP/
├── app.py                  # Flask web server
├── scraper_backend.py      # Scraper engine
├── templates/
│   └── index.html         # Web interface
├── requirements.txt        # Dependencies
├── .gitignore             # Git ignore rules
└── output/                # Generated data
```

## 🌐 Deployment

### Option 1: Local Deployment

```bash
python app.py
```

Access at `http://localhost:5000`

### Option 2: Production Deployment (Gunicorn)

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option 3: Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:

```bash
docker build -t inspire-scraper .
docker run -p 5000:5000 -v $(pwd)/output:/app/output inspire-scraper
```

## ⚙️ Environment Variables (Optional)

Create `.env` file:

```env
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5000
```

## 📝 API Endpoints

- `GET /` - Web interface
- `GET /api/states` - Get list of states
- `GET /api/districts/<state_id>` - Get districts for state
- `POST /api/start` - Start scraping
- `GET /api/status` - Get scraping status
- `GET /api/download` - Download results

## 🔒 Security Notes

For production deployment:
1. Set `debug=False` in `app.py`
2. Use a reverse proxy (nginx/Apache)
3. Enable HTTPS
4. Set up rate limiting
5. Configure firewall rules

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Change port in app.py
app.run(port=8080)
```

**Dependencies not installing:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**No data scraped:**
- Check logs in `output/scraper.log`
- Verify internet connection
- Ensure website is accessible

## 📄 License

This project is for educational purposes only.

## 🤝 Support

For issues or questions, check `output/scraper.log` for detailed error messages.

---

**Version:** 2.0  
**Last Updated:** December 2025
