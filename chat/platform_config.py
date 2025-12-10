"""
Platform Configuration for Multi-Platform Legal Chatbot Comparison
Stores credentials and selectors for different legal chatbot platforms
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Platform configurations for web scraping
PLATFORMS = {
    'qanoonmate': {
        'name': 'QanoonMate',
        'url': 'https://www.qanoonmate.com/chat',
        'requires_login': False,
        'credentials': {},
        'selectors': {
            'input_field': 'textarea[placeholder*="message"], textarea[placeholder*="ask"], textarea',
            'submit_button': 'button[type="submit"]',
            'response_container': '.message.bot, [class*="bot-message"], [class*="bot-response"]'
        },
        'wait_times': {
            'page_load': 10,
            'response': 35
        }
    },
    
    'lexa_lawyer': {
        'name': 'Lexa Lawyer',
        'url': 'https://www.lexa.lawyer/chatbot',
        'requires_login': True,
        'credentials': {
            'email': os.getenv('LEXA_EMAIL', 'muhammadhassanfarid@gmail.com'),
            'password': os.getenv('LEXA_PASSWORD', 'Wazirwazir#786')
        },
        'selectors': {
            'login_email': 'input[type="email"], input[name="email"], #email',
            'login_password': 'input[type="password"], input[name="password"], #password',
            'login_button': 'button[type="submit"], button:contains("Login"), button:contains("Sign In")',
            'input_field': 'textarea[placeholder*="message"], input[placeholder*="ask"], textarea, #chat-input',
            'submit_button': 'button[type="submit"], button:contains("Send"), [aria-label*="send"]',
            'response_container': '.message.bot, [class*="bot-message"], [class*="response"], [class*="assistant"]'
        },
        'wait_times': {
            'page_load': 15,
            'login': 10,
            'response': 30
        }
    },
    
    'lawbrains': {
        'name': 'LawBrains',
        'url': 'https://www.lawbrains.com/chatbot',
        'requires_login': True,
        'credentials': {
            'email': os.getenv('LAWBRAINS_EMAIL', ''),
            'password': os.getenv('LAWBRAINS_PASSWORD', '')
        },
        'selectors': {
            'login_email': 'input[type="email"], input[name="email"], #email',
            'login_password': 'input[type="password"], input[name="password"], #password',
            'login_button': 'button[type="submit"], button:contains("Login")',
            'input_field': 'textarea[placeholder*="message"], input[placeholder*="ask"]',
            'submit_button': 'button[type="submit"], button:contains("Send")',
            'response_container': '.message.bot, [class*="bot-message"]'
        },
        'wait_times': {
            'page_load': 15,
            'login': 10,
            'response': 25
        }
    },
    
    'jurisai': {
        'name': 'JurisAI',
        'url': 'https://www.jurisai.com/chat',
        'requires_login': True,
        'credentials': {
            'username': os.getenv('JURISAI_USERNAME', ''),
            'password': os.getenv('JURISAI_PASSWORD', '')
        },
        'selectors': {
            'login_username': 'input[type="text"], input[name="username"]',
            'login_password': 'input[type="password"], input[name="password"]',
            'login_button': 'button[type="submit"], button:contains("Login")',
            'input_field': 'textarea[placeholder*="message"]',
            'submit_button': 'button[type="submit"], button:contains("Send")',
            'response_container': '.message.bot, [class*="bot-message"]'
        },
        'wait_times': {
            'page_load': 15,
            'login': 10,
            'response': 25
        }
    }
}

# Default configuration for any platform
DEFAULT_CONFIG = {
    'wait_times': {
        'page_load': 15,
        'login': 10,
        'response': 30
    },
    'selectors': {
        'input_field': 'textarea, input[placeholder*="message"], input[placeholder*="ask"]',
        'submit_button': 'button[type="submit"], button:contains("Send")',
        'response_container': '.message.bot, [class*="bot-message"], [class*="response"]'
    }
}

def get_platform_config(platform_name):
    """Get configuration for a specific platform"""
    platform_name = platform_name.lower().strip()
    if platform_name in PLATFORMS:
        return PLATFORMS[platform_name]
    return None

def validate_credentials(platform_name):
    """Validate that required credentials are configured"""
    config = get_platform_config(platform_name)
    if not config:
        return False, f"Platform '{platform_name}' not found"
    
    if config['requires_login']:
        credentials = config.get('credentials', {})
        if not credentials.get('email') and not credentials.get('username'):
            return False, f"Missing credentials for {config['name']}"
    
    return True, "Credentials valid"

def list_available_platforms():
    """List all available platforms"""
    return {
        name: {
            'display_name': config['name'],
            'requires_login': config['requires_login'],
            'url': config['url']
        }
        for name, config in PLATFORMS.items()
    }
