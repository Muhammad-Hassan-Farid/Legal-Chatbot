# PakLegal ChatBot - Production Deployment Guide

## Overview
This guide will help you deploy the PakLegal ChatBot to a production server using Gunicorn and Nginx.

## Prerequisites
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.12+
- ffmpeg installed
- Nginx web server
- SSL certificate (Let's Encrypt recommended)
- OpenAI API key

## Quick Start (Automated)

### Option 1: Using the deployment script
```bash
chmod +x deploy.sh
sudo ./deploy.sh your-domain.com
```

### Option 2: Manual Setup

#### 1. Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

#### 2. Install Dependencies
```bash
sudo apt-get install -y python3.12 python3-pip python3-venv nginx git curl certbot python3-certbot-nginx ffmpeg postgresql postgresql-contrib
```

#### 3. Create Application User
```bash
sudo useradd -m -s /bin/bash paklegal
sudo su - paklegal
```

#### 4. Clone the Repository
```bash
cd ~
git clone https://github.com/yourusername/Pakistan-Constitution-Chatbot.git
cd Pakistan-Constitution-Chatbot
```

#### 5. Setup Virtual Environment
```bash
python3 -m venv myenv
source myenv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. Configure Environment Variables
```bash
cat > .env << EOF
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
SECRET_KEY=$(openssl rand -base64 32)
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://user:password@localhost/paklegal_db
EOF
```

#### 7. Collect Static Files
```bash
python manage.py collectstatic --noinput
python manage.py migrate
```

#### 8. Test with Gunicorn
```bash
gunicorn --config gunicorn_config.py paklegal_chatbot.wsgi:application
```

#### 9. Setup Systemd Service
```bash
sudo cp paklegal-chatbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable paklegal-chatbot
```

#### 10. Configure Nginx
```bash
sudo cp nginx.conf /etc/nginx/sites-available/paklegal-chatbot
sudo ln -sf /etc/nginx/sites-available/paklegal-chatbot /etc/nginx/sites-enabled/paklegal-chatbot
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

#### 11. Setup SSL Certificate
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

#### 12. Start the Application
```bash
sudo systemctl start paklegal-chatbot
sudo systemctl status paklegal-chatbot
```

## Monitoring and Maintenance

### Check Application Status
```bash
sudo systemctl status paklegal-chatbot
```

### View Application Logs
```bash
sudo journalctl -u paklegal-chatbot -f
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/gunicorn/access.log
```

### Restart Application
```bash
sudo systemctl restart paklegal-chatbot
```

### Update Application
```bash
cd /home/paklegal/Pakistan-Constitution-Chatbot
git pull origin main
source myenv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart paklegal-chatbot
```

## Performance Optimization

### 1. Database Optimization
- Use PostgreSQL for production (configured in settings.py)
- Enable connection pooling with pgBouncer
- Regular backups: `pg_dump paklegal_db > backup.sql`

### 2. Caching
- Redis is recommended for caching embeddings and LLM responses
- Configure in Django settings for session and cache storage

### 3. Load Balancing
For high-traffic scenarios, setup multiple Gunicorn workers:
```bash
# In gunicorn_config.py
workers = multiprocessing.cpu_count() * 2 + 1
```

### 4. CDN Integration
- Use CloudFlare or AWS CloudFront for static files and images
- Configure cache headers in nginx.conf

## Security Checklist

- [ ] Change Django SECRET_KEY in .env
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS properly
- [ ] Enable HTTPS/SSL
- [ ] Setup firewall rules
- [ ] Enable Django CSRF protection
- [ ] Configure CORS if needed
- [ ] Regular security updates: `sudo apt update && sudo apt upgrade`
- [ ] Monitor error logs for suspicious activity
- [ ] Use strong OpenAI API key management

## Troubleshooting

### Application won't start
```bash
sudo journalctl -u paklegal-chatbot -n 50
```

### Nginx not serving static files
```bash
sudo python manage.py collectstatic --noinput --clear
sudo chown -R www-data:www-data /home/paklegal/Pakistan-Constitution-Chatbot/static
```

### High memory usage
- Check number of Gunicorn workers
- Monitor embeddings model loading
- Consider implementing caching layer

### Slow transcription/synthesis
- Ensure ffmpeg is properly installed
- Monitor CPU usage during voice operations
- Consider running voice processing in background tasks (Celery)

## Backup and Recovery

### Regular Backups
```bash
# Database backup
pg_dump paklegal_db > /backups/paklegal_$(date +%Y%m%d).sql

# Application files
tar -czf /backups/paklegal_$(date +%Y%m%d).tar.gz /home/paklegal/Pakistan-Constitution-Chatbot
```

### Recovery
```bash
# Restore database
psql paklegal_db < backup.sql

# Restore application
tar -xzf backup.tar.gz -C /
```

## Support and Documentation

- Django: https://docs.djangoproject.com/
- Gunicorn: https://gunicorn.org/
- Nginx: https://nginx.org/
- LangChain: https://python.langchain.com/
- OpenAI: https://platform.openai.com/docs/

