from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def landing_page(request):
    """
    Render the landing page.
    """
    return render(request, 'core/landing.html')


@login_required
def home_page(request):
    """
    Render the home page for authenticated users.
    """
    return render(request, 'core/home.html')