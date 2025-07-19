from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from PIL import Image
import os

@login_required
def dashboard_home(request):
    """
    Main dashboard view for authenticated users
    """
    context = {
        'user': request.user,
        'page_title': 'Dashboard',
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
def upload_image(request):
    """
    View for uploading crop images for diagnosis
    """
    if request.method == 'POST':
        return handle_image_upload(request)
    
    context = {
        'user': request.user,
        'page_title': 'Upload Image',
    }
    return render(request, 'dashboard/upload.html', context)

def handle_image_upload(request):
    """
    Handle the actual image upload and trigger AI diagnosis
    """
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image file provided'}, status=400)
        
        uploaded_file = request.FILES['image']
        
        # Validate file type
        if not uploaded_file.content_type.startswith('image/'):
            return JsonResponse({'error': 'Invalid file type. Please upload an image.'}, status=400)
        
        # Validate file size (10MB max)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Maximum size is 10MB.'}, status=400)
        
        # Get image dimensions
        try:
            image = Image.open(uploaded_file)
            width, height = image.size
            uploaded_file.seek(0)  # Reset file pointer
        except Exception:
            return JsonResponse({'error': 'Invalid image file.'}, status=400)
        
        # Get production models
        production_models = MLModel.objects.filter(status='production')
        if not production_models.exists():
            return JsonResponse({'error': 'No production models available for diagnosis.'}, status=400)
        
        # Use the first production model (you can implement selection logic later)
        model = production_models.first()
        
        # Make prediction using the production model
        try:
            prediction_result = make_prediction(model.id, uploaded_file, request.user, uploaded_file.name)
            
            # Prepare response data
            response_data = {
                'success': True,
                'prediction_id': prediction_result.id,
                'prediction': prediction_result.prediction,
                'confidence': prediction_result.confidence_score,
                'disease_name': prediction_result.disease_name,
                'disease_description': prediction_result.disease_description,
                'severity': prediction_result.severity,
                'recommendations': prediction_result.recommendations,
                'processing_time': prediction_result.processing_time,
                'model_used': model.name,
                'image_url': prediction_result.image.url if prediction_result.image else None,
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Prediction failed: {str(e)}'
            }, status=500)
        
    except Exception as e:
        return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)

@login_required
def my_diagnoses(request):
    """
    View for showing user's diagnosis history
    """
    diagnoses = PredictionResult.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    context = {
        'user': request.user,
        'page_title': 'My Diagnoses',
        'diagnoses': diagnoses,
    }
    return render(request, 'dashboard/my_diagnoses.html', context)

@login_required
def profile(request):
    """User profile view"""
    from accounts.models import UserProfile
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = None
    
    context = {
        'user_profile': user_profile,
        'user': request.user,
        'page_title': 'Profile',
    }
    
    return render(request, 'dashboard/profile.html', context)
