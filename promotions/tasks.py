"""
Celery Tasks for Promotions App.

Handles async email and SMS sending for gift card transfers.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from config.utils.sns_services import sms_service
from config.utils.ses_mailer import ses_mailer

logger = logging.getLogger(__name__)

