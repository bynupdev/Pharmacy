# from django.shortcuts import redirect
# from .models import Pharmacy

# class PharmacyMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
    
#     def __call__(self, request):
#         # Get pharmacy from session
#         pharmacy_id = request.session.get('pharmacy_id')
#         if pharmacy_id and request.user.is_authenticated:
#             try:
#                 request.pharmacy = Pharmacy.objects.get(id=pharmacy_id)
#             except Pharmacy.DoesNotExist:
#                 request.pharmacy = None
#         else:
#             request.pharmacy = None
        
#         response = self.get_response(request)
#         return response

from django.shortcuts import redirect
from django.urls import reverse
from .models import Pharmacy

class PharmacyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Set default
        request.pharmacy = None
        
        # Skip for public paths
        public_paths = ['/login/', '/register/', '/logout/', '/admin/', '/static/', '/media/']
        if any(request.path.startswith(path) for path in public_paths):
            return self.get_response(request)
        
        # Get pharmacy from user's profile
        if request.user.is_authenticated:
            try:
                if hasattr(request.user, 'profile') and request.user.profile:
                    request.pharmacy = request.user.profile.pharmacy
                    
                    # Debug output (remove in production)
                    if request.pharmacy:
                        print(f"Middleware: Pharmacy set to {request.pharmacy.name}")
                    else:
                        print(f"Middleware: No pharmacy for user {request.user.username}")
            except Exception as e:
                print(f"Middleware error: {e}")
                request.pharmacy = None
        
        response = self.get_response(request)
        return response