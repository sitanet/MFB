import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class AutoLogoutMiddleware:
    """
    Middleware to automatically log out users after 5 minutes of inactivity.
    Tracks user activity and enforces session timeout.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Session timeout in seconds (5 minutes = 300 seconds)
        self.timeout = getattr(settings, 'AUTO_LOGOUT_TIMEOUT', 1200)
        
    def __call__(self, request):
        # Skip middleware for unauthenticated users and specific paths
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        # Skip timeout check for logout, login, and API check endpoints
        excluded_paths = [
            reverse('logout'),
            reverse('login'),
            '/api/check-session/',
            '/api/extend-session/',
        ]
        
        if request.path in excluded_paths:
            return self.get_response(request)
        
        # Get current time
        current_time = time.time()
        
        # Get last activity time from session
        last_activity = request.session.get('last_activity')
        
        if last_activity:
            # Calculate time since last activity
            time_since_activity = current_time - last_activity
            
            # Check if session has expired
            if time_since_activity > self.timeout:
                logger.info(f"Session expired for user {request.user.username} after {time_since_activity} seconds of inactivity")
                
                # Log out the user
                logout(request)
                
                # Handle AJAX requests differently
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'session_expired',
                        'message': 'Your session has expired due to inactivity. Please log in again.',
                        'redirect_url': reverse('login')
                    }, status=401)
                
                # For regular requests, redirect to login with message
                return redirect(reverse('login') + '?timeout=1')
        
        # Update last activity time in session
        request.session['last_activity'] = current_time
        
        response = self.get_response(request)
        return response