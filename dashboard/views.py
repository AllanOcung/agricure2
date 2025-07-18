from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.contrib import messages
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
import os
import json
from .models import CropImage, DiagnosisResult, Disease


User = get_user_model()

@login_required
def dashboard_home(request):
    """
    Main dashboard view for authenticated users
    """
    # Get recent diagnoses for the user
    recent_diagnoses = DiagnosisResult.objects.filter(
        crop_image__user=request.user,
        status='completed'
    ).order_by('-created_at')[:5]
    
    # Get diagnosis statistics
    total_diagnoses = DiagnosisResult.objects.filter(
        crop_image__user=request.user,
        status='completed'
    ).count()
    
    diseased_count = DiagnosisResult.objects.filter(
        crop_image__user=request.user,
        status='completed',
        is_diseased=True
    ).count()
    
    context = {
        'user': request.user,
        'page_title': 'Dashboard',
        'recent_diagnoses': recent_diagnoses,
        'total_diagnoses': total_diagnoses,
        'diseased_count': diseased_count,
        'healthy_count': total_diagnoses - diseased_count,
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
def profile_view(request):
    """
    User profile management view
    """
    context = {
        'user': request.user,
        'page_title': 'Profile',
    }
    return render(request, 'dashboard/profile.html', context)

@login_required
def diagnosis_history(request):
    """
    View for showing user's diagnosis history
    """
    diagnoses = DiagnosisResult.objects.filter(
        crop_image__user=request.user
    ).order_by('-created_at')
    
    context = {
        'user': request.user,
        'page_title': 'Diagnosis History',
        'diagnoses': diagnoses,
    }
    return render(request, 'dashboard/diagnosis_history.html', context)

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
        
        # Create CropImage instance
        crop_image = CropImage.objects.create(
            user=request.user,
            image=uploaded_file,
            crop_type=request.POST.get('crop_type', ''),
            location=request.POST.get('location', ''),
            notes=request.POST.get('notes', ''),
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            image_width=width,
            image_height=height
        )
        
        # Trigger AI diagnosis
        try:
            diagnosis = ai_service.diagnose_crop_image(crop_image)
            
            # Prepare response data
            response_data = {
                'success': True,
                'diagnosis_id': diagnosis.id,
                'crop_image_id': crop_image.id,
                'status': diagnosis.status,
            }
            
            if diagnosis.status == 'completed':
                response_data.update({
                    'is_diseased': diagnosis.is_diseased,
                    'detected_disease': diagnosis.detected_disease.name if diagnosis.detected_disease else 'Healthy',
                    'confidence_score': diagnosis.confidence_score,
                    'severity': diagnosis.severity,
                    'recommendations': diagnosis.recommendations,
                    'processing_time': diagnosis.processing_time,
                })
            elif diagnosis.status == 'failed':
                response_data['error'] = diagnosis.error_message
            
            return JsonResponse(response_data)
            
        except Exception as e:
            # If AI diagnosis fails, still save the image
            return JsonResponse({
                'success': True,
                'crop_image_id': crop_image.id,
                'status': 'failed',
                'error': f'AI diagnosis failed: {str(e)}'
            })
        
    except Exception as e:
        return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)

@login_required
def diagnosis_detail(request, diagnosis_id):
    """
    View for displaying detailed diagnosis results
    """
    diagnosis = get_object_or_404(
        DiagnosisResult, 
        id=diagnosis_id, 
        crop_image__user=request.user
    )
    
    context = {
        'user': request.user,
        'page_title': 'Diagnosis Details',
        'diagnosis': diagnosis,
    }
    return render(request, 'dashboard/diagnosis_detail.html', context)
