import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here'
    
    # Set SERVER_NAME dynamically for production
    # Remove or comment this line for local testing
    SERVER_NAME = os.environ.get('https://smartclassroommanagamentsystem.onrender.com')  # e.g., "managementofsmartclassroom-1.onrender.com"
    
    # Flask-Mail settings
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
