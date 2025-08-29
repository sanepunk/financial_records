# Contract Intelligence Parser API

A sophisticated AI-powered contract analysis and data extraction system for accounts receivable SaaS platforms. The system automatically processes contracts, extracts critical financial and operational data, and provides confidence scores and gap analysis.

## 🚀 Features

- **Simple Contract Processing**: Direct file upload with background processing
- **AI-Powered Data Extraction**: Uses advanced LLM models for intelligent contract parsing
- **OCR Integration**: Extracts text from PDF contracts using OCR Space API
- **Comprehensive Data Extraction**: Extracts parties, financial details, payment terms, SLAs, and more
- **Scoring Algorithm**: Weighted scoring system (0-100 points) with confidence levels
- **Gap Analysis**: Identifies missing critical fields and provides recommendations
- **RESTful API**: Clean, well-documented API endpoints
- **Simple Architecture**: Built with FastAPI and MongoDB for easy deployment
- **Docker Support**: Fully containerized for easy deployment

## 🏗️ Architecture

```
├── FastAPI Backend (API Layer)
├── MongoDB (Data Storage)
├── OCR Space API (Text Extraction)
└── Google AI (Gemini) API (AI Analysis)
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── contracts.py          # Contract API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # Application configuration
│   │   └── database.py           # MongoDB connection
│   ├── models/
│   │   ├── __init__.py
│   │   └── contract.py           # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service_robust.py  # AI contract analysis
│   │   ├── contract_service.py   # Contract business logic
│   │   └── ocr_service.py        # OCR text extraction
│   └── __init__.py
├── uploads/                      # File storage directory
├── .env                         # Environment variables
├── .env.example                 # Environment template
├── docker-compose.yml           # Simple deployment
├── Dockerfile                   # Container configuration
├── main.py                     # FastAPI application
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OCR Space API key
- Google AI (Gemini) API key

### 1. Clone the Repository

```bash
git clone <repository-url>
cd contract-intelligence-parser/backend
```

### 2. Environment Configuration

Copy the environment template and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# API Keys (Required)
OCR_SPACE_API_KEY=your_ocr_space_api_key_here
GOOGLE_AI_API_KEY=your_google_ai_api_key_here

# Other configurations are set to defaults for Docker
```

### 3. Deploy with Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
```

Services will be available at:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MongoDB**: localhost:27017

### 4. Manual Setup (Development)

If you prefer to run without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Start MongoDB (required)
# MongoDB: mongod --port 27017

# Start the API
uvicorn main:app --reload --port 8000
```

## 📚 API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### 1. Upload Contract
```http
POST /contracts/upload
Content-Type: multipart/form-data

Parameters:
- file: PDF file (max 50MB)

Response:
{
  "contract_id": "uuid",
  "message": "Contract uploaded successfully",
  "status": "pending"
}
```

#### 2. Check Processing Status
```http
GET /contracts/{contract_id}/status

Response:
{
  "contract_id": "uuid",
  "status": "pending|processing|completed|failed",
  "progress_percentage": 75.0,
  "error_details": null,
  "created_at": "2025-08-29T10:00:00",
  "updated_at": "2025-08-29T10:05:00"
}
```

#### 3. Get Contract Data
```http
GET /contracts/{contract_id}

Response: Complete contract data with extracted information
(Only available when status is "completed")
```

#### 4. List Contracts
```http
GET /contracts?page=1&limit=10&status=completed

Response:
{
  "contracts": [...],
  "total": 25,
  "page": 1,
  "limit": 10,
  "has_next": true,
  "has_prev": false
}
```

#### 5. Download Original File
```http
GET /contracts/{contract_id}/download

Response: Original PDF file
```

## 🔍 Data Extraction

The system extracts and scores the following information:

### Extracted Fields
1. **Party Identification** (25 points)
   - Contract parties, legal entities, signatories

2. **Account Information** (10 points)
   - Billing details, account numbers, contacts

3. **Financial Details** (30 points)
   - Line items, totals, currency, tax information

4. **Payment Structure** (20 points)
   - Payment terms, schedules, methods

5. **Revenue Classification** (Confidence scoring)
   - Recurring vs. one-time payments, billing cycles

6. **Service Level Agreements** (15 points)
   - Performance metrics, penalties, support terms

### Confidence Scoring
- Each field receives a confidence score (0.0 - 1.0)
- Overall contract score calculated using weighted system
- Gap analysis identifies missing or low-confidence fields

## 🧪 Testing

### API Testing with curl

```bash
# Upload a contract
curl -X POST "http://localhost:8000/api/v1/contracts/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_contract.pdf"

# Check status
curl "http://localhost:8000/api/v1/contracts/{contract_id}/status"

# Get contract data
curl "http://localhost:8000/api/v1/contracts/{contract_id}"
```

### Test Cases to Validate

1. **Valid PDF Upload**: Upload a standard contract PDF
2. **Invalid File Type**: Try uploading non-PDF files
3. **Large File**: Test with files approaching 50MB limit
4. **Missing Information**: Test with contracts lacking key fields
5. **Multiple Contracts**: Upload several contracts simultaneously
6. **Status Polling**: Monitor processing progress
7. **Error Handling**: Test API responses for various error conditions

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `OCR_SPACE_API_KEY` | OCR Space API key | Required |
| `GOOGLE_AI_API_KEY` | Google AI API key | Required |
| `MAX_FILE_SIZE` | Maximum upload size (bytes) | `52428800` (50MB) |
| `UPLOAD_DIR` | File storage directory | `./uploads` |
| `DEBUG` | Debug mode | `True` |

### Scaling Configuration

For production deployment:

1. **Multiple API Instances**: Scale horizontally with load balancer

2. **Database**: Configure MongoDB replica set

3. **Load Balancing**: Use nginx or similar for API load balancing

## 📊 Monitoring

### Application Logs
```bash
# API logs
docker-compose logs -f api

# All services
docker-compose logs -f
```

### Health Checks
```bash
# Basic health check
curl http://localhost:8000/health

# API status
curl http://localhost:8000/
```

## 🚨 Error Handling

The system implements comprehensive error handling:

- **File Validation**: MIME type checking, size limits
- **Processing Errors**: Retry mechanisms with exponential backoff
- **API Errors**: Proper HTTP status codes and error messages
- **Database Errors**: Connection retry and graceful degradation
- **External API Failures**: Fallback mechanisms and error reporting

## 🔒 Security Considerations

- File type validation (PDF only)
- File size limits (50MB)
- Input sanitization
- Error message sanitization
- API rate limiting (implement as needed)
- Secure API key storage

## 🎯 Success Criteria

✅ **Functionality**: All API endpoints operational  
✅ **Architecture**: Clean, modular, scalable design  
✅ **Error Handling**: Comprehensive error management  
✅ **Documentation**: Detailed setup and usage instructions  
✅ **Deployment**: Docker-based deployment ready  
✅ **Performance**: Handles 50MB files efficiently  
✅ **Reliability**: Background processing with retry mechanisms  

## 🔄 Development Workflow

1. **Development Setup**: Use manual setup for development
2. **Testing**: Test with various contract formats
3. **Docker Build**: Build and test in containerized environment
4. **Production Deploy**: Use docker-compose for production

## 📞 Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review application logs
3. Verify environment configuration
4. Test with sample contracts

---

**Contract Intelligence Parser API v1.0.0**  
Built with FastAPI, MongoDB, and AI-powered analysis.
