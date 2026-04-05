from django.shortcuts import redirect
from .models import Pharmacy

class PharmacyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get pharmacy from session
        pharmacy_id = request.session.get('pharmacy_id')
        if pharmacy_id and request.user.is_authenticated:
            try:
                request.pharmacy = Pharmacy.objects.get(id=pharmacy_id)
            except Pharmacy.DoesNotExist:
                request.pharmacy = None
        else:
            request.pharmacy = None
        
        response = self.get_response(request)
        return response