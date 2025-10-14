# AI Data Analyst Platform

A comprehensive data analysis platform with AI-powered insights, interactive dashboards, and natural language querying. Built with React frontend, Django backend, and LLaMA AI model integration.

## Features

- **File Upload & Processing**: Upload Excel/CSV files or connect Google Sheets
- **Natural Language Queries**: Ask questions about your data in plain English
- **AI-Powered Insights**: Automatic KPI detection, trend analysis, anomaly detection
- **Interactive Dashboards**: Customizable visualizations with Plotly
- **Theme Customization**: Dynamic color schemes with accessibility compliance
- **Export Functionality**: Download dashboards as PDF or images
- **Real-time Chat**: Conversational interface with AI assistant

## Architecture

### Backend (Django)
- **Authentication**: Supabase integration for user management
- **File Processing**: Data cleaning and preprocessing with pandas
- **AI Integration**: LLaMA 70B model via Grok Cloud API
- **SQL Generation**: Natural language to SQL conversion
- **Dashboard Generation**: Interactive Plotly visualizations
- **Export System**: PDF and image generation

### Frontend (React + TypeScript)
- **Authentication**: Supabase Auth with protected routes
- **File Management**: Drag-and-drop upload interface
- **Chat Interface**: Real-time conversation with AI
- **Dashboard Viewer**: Interactive data visualizations
- **Theme Editor**: Color customization with contrast checking

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- Supabase account
- Grok Cloud API access

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   Create a `.env` file in the backend directory:
   ```env
   # Django Settings
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1

   # CORS Settings
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

   # Supabase Settings
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

   # AI Model Settings
   GROK_API_KEY=your-grok-api-key
   GROK_API_URL=https://api.grok.com/v1
   LLAMA_MODEL=llama-70b
   ```

5. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start Django server:**
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**

   Create a `.env` file in the frontend directory:
   ```env
   REACT_APP_SUPABASE_URL=https://your-project.supabase.co
   REACT_APP_SUPABASE_ANON_KEY=your-supabase-anon-key
   REACT_APP_API_URL=http://localhost:8000/api
   ```

4. **Start React development server:**
   ```bash
   npm start
   ```

## API Keys Configuration

### Supabase Setup

1. **Create Supabase project:**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Go to Settings > API
   - Copy the Project URL and anon/public key

2. **Configure authentication:**
   - Go to Authentication > Settings
   - Configure site URL: `http://localhost:3000`
   - Enable email confirmations if needed

3. **Set up storage bucket:**
   - Go to Storage > Buckets
   - Create a new bucket named `data-files`
   - Set bucket as public

### Grok Cloud API Setup

1. **Get Grok API access:**
   - Visit [Grok Cloud](https://grok.com) or your AI provider
   - Sign up for API access
   - Generate an API key for LLaMA 70B model

2. **Configure API endpoint:**
   - Use the provided API URL (typically `https://api.grok.com/v1`)
   - Specify the model as `llama-70b` or your preferred model

## Usage

1. **Sign up/Login** to the platform
2. **Upload data** (Excel/CSV) or connect Google Sheets
3. **Ask questions** in natural language about your data
4. **Generate dashboards** with automatic insights
5. **Customize themes** and export results

## Project Structure

```
├── backend/
│   ├── backend/           # Django project settings
│   ├── users/            # User authentication
│   ├── files/            # File upload/management
│   ├── ai/               # AI endpoints
│   └── ml_models/        # AI/ML components
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   └── context/      # React context
│   └── public/           # Static assets
```

## Development

### Backend Development
- Models: `backend/*/models.py`
- Views: `backend/*/views.py`
- Serializers: `backend/*/serializers.py`
- Tests: `backend/*/tests.py`

### Frontend Development
- Components: `frontend/src/components/`
- Pages: `frontend/src/pages/`
- Services: `frontend/src/services/`
- Types: `frontend/src/types/`

## Deployment

### Backend Deployment
```bash
# Production settings
DEBUG=False
SECRET_KEY=<secure-secret-key>
ALLOWED_HOSTS=<your-domain>

# Use PostgreSQL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '<db-name>',
        'USER': '<db-user>',
        'PASSWORD': '<db-password>',
        'HOST': '<db-host>',
        'PORT': '5432',
    }
}
```

### Frontend Deployment
```bash
npm run build
# Deploy build/ folder to your hosting service
```

## API Documentation

### Authentication Endpoints
- `POST /api/users/login/` - User login
- `POST /api/users/signup/` - User registration
- `POST /api/users/verify-token/` - Token verification

### File Management Endpoints
- `POST /api/files/upload/` - Upload file
- `POST /api/files/google-sheet/` - Connect Google Sheet
- `GET /api/files/list/` - List files
- `GET /api/files/preview/{id}/` - Get file preview
- `DELETE /api/files/delete/{id}/` - Delete file

### AI/Chat Endpoints
- `POST /api/ai/chat/` - Send chat message
- `POST /api/ai/dashboard/` - Generate dashboard
- `GET /api/ai/dashboard/{id}/` - Get dashboard
- `POST /api/ai/dashboard/{id}/export/` - Export dashboard

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details
