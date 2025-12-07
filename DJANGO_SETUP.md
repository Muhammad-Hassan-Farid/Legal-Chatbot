# Django Setup Guide for PakLegal

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Run migrations (if needed):**
   ```bash
   python manage.py migrate
   ```

4. **Collect static files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

5. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   - Landing page: http://127.0.0.1:8000/
   - Chat interface: http://127.0.0.1:8000/chat/
   - API endpoint: http://127.0.0.1:8000/get/

## Project Structure

```
paklegal_chatbot/          # Django project settings
├── settings.py            # Main settings file
├── urls.py                # Root URL configuration
├── wsgi.py                # WSGI configuration
└── asgi.py                # ASGI configuration

chat/                      # Django app
├── views.py               # View functions
├── urls.py                # App URL configuration
├── services.py            # RAG chain service (singleton)
├── models.py              # Database models (if needed)
└── admin.py               # Admin configuration

templates/                 # HTML templates
├── landing.html           # Landing page
└── chat.html              # Chat interface

static/                    # Static files
└── style.css              # Stylesheet

src/                       # Source modules
├── helper.py              # Helper functions
└── prompt.py              # System prompts
```

## Key Differences from Flask

1. **URL Routing:** Uses Django's URL patterns instead of Flask decorators
2. **Templates:** Uses Django template syntax (`{% static %}` instead of `url_for()`)
3. **Views:** Function-based views instead of Flask route decorators
4. **Settings:** Centralized in `settings.py` instead of app configuration
5. **Static Files:** Configured in `settings.py` with `STATIC_URL` and `STATICFILES_DIRS`

## Running on Different Port

To run on port 8080 (like the Flask version):
```bash
python manage.py runserver 0.0.0.0:8080
```

## Production Deployment

For production, you'll need to:
1. Set `DEBUG = False` in `settings.py`
2. Configure `ALLOWED_HOSTS` properly
3. Set up a proper WSGI server (e.g., Gunicorn)
4. Configure static file serving (e.g., WhiteNoise or nginx)
5. Use environment variables for sensitive settings

