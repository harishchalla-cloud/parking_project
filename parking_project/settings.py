"""
Django settings for parking_project project.
"""

import os
import sys
import logging
from pathlib import Path
from decouple import config
import boto3
import pymysql

# Install pymysql as MySQLdb for Django
pymysql.install_as_MySQLdb()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
IS_LOCAL = 'runserver' in sys.argv
logger = logging.getLogger(__name__)

# Update ALLOWED_HOSTS for the new Elastic Beanstalk environment
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'parkingapp-env.eba-pjwcyf2j.us-east-1.elasticbeanstalk.com',
    '.elasticbeanstalk.com',
    '3.224.197.135',
    '*'
]

logger.info(f"DEBUG={DEBUG}, IS_LOCAL={IS_LOCAL}, ALLOWED_HOSTS={ALLOWED_HOSTS}")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'parking.apps.ParkingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'parking_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'parking' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'parking_project.wsgi.application'

# Database settings (RDS)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'x23417498_db',
        'USER': 'admin',
        'PASSWORD': 'zxcvbnm1234567',
        'HOST': 'parkingdb-instance.cb3ysdqsmzfo.us-east-1.rds.amazonaws.com',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES',
        },
    }
}

# AWS settings
AWS_REGION = 'us-east-1'
# Remove explicit AWS credentials since boto3 will use the default profile
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are not needed here

# S3 settings for media and static files
AWS_STORAGE_BUCKET_NAME = 'x23417498-parking-s3'  # Updated to match the bucket you created
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'  # Updated to standard S3 domain format
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'private'
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
AWS_QUERYSTRING_AUTH = False
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Static files (using the same bucket)
AWS_STATIC_BUCKET_NAME = 'x23417498-parking-s3'  # Updated to match the bucket you created
STATIC_URL = f'https://{AWS_STATIC_BUCKET_NAME}.s3.amazonaws.com/static/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# SNS configuration
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:296779434624:ParkingNotifications'

# CloudWatch logging (already configured in ParkingUtils.log_to_cloudwatch)
# Log group: ParkingLogs, Log stream: ApplicationStream (matches your script)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGOUT_REDIRECT_URL = 'parking:parking_list'
LOGIN_REDIRECT_URL = '/parking/'
LOGIN_URL = '/accounts/login/'

# Security settings for production
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=not IS_LOCAL, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not IS_LOCAL, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=not IS_LOCAL, cast=bool)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

NOTIFICATION_FALLBACK_METHOD = 'cloudwatch'

