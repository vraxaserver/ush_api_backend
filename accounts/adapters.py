"""
Custom Allauth Adapter.

Overrides default allauth behavior to:
- Disable allauth's email sending (we use our own verification system)
- Customize user creation
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter that disables allauth's email sending.
    
    We use our own verification code system instead of allauth's
    email confirmation links.
    """

    def send_mail(self, template_prefix, email, context):
        """
        Override to prevent allauth from sending any emails.
        
        Our app handles email sending through Celery tasks in signals.py
        """
        # Do nothing - we handle emails ourselves
        pass

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Override to prevent allauth from sending confirmation emails.
        """
        # Do nothing - we use verification codes instead
        pass

    def is_open_for_signup(self, request):
        """
        Allow signups.
        """
        return True

    def save_user(self, request, user, form, commit=True):
        """
        Saves a new `User` instance using information provided in the
        signup form.
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Additional custom fields can be handled here
        data = form.cleaned_data if hasattr(form, 'cleaned_data') else {}
        
        if commit:
            user.save()
        
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter.
    """

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed.
        """
        pass

    def populate_user(self, request, sociallogin, data):
        """
        Hook to populate user instance from social account data.
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Extract additional data from social login
        if not user.first_name:
            user.first_name = data.get("first_name", "")
        if not user.last_name:
            user.last_name = data.get("last_name", "")
        
        return user
