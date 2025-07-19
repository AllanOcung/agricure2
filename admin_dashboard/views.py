from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from django.core.files.base import ContentFile
from datetime import datetime, timedelta
import zipfile
import os
from PIL import Image
import logging

from dashboard.decorators import role_required
from dataset_management.models import Dataset, DatasetImage, DatasetClass

logger = logging.getLogger('admin_dashboard')



@login_required
@role_required(['admin'])
def admin_dashboard_home(request):
    """Admin dashboard home page"""
    
    # Get summary statistics from dataset management
    total_datasets = Dataset.objects.count()
    completed_datasets = Dataset.objects.filter(status='completed').count()
    processing_datasets = Dataset.objects.filter(status='processing').count()
    failed_datasets = Dataset.objects.filter(status='failed').count()
    
    # Recent activity
    recent_datasets = Dataset.objects.order_by('-created_at')[:5]
    total_images = DatasetImage.objects.count()
    total_classes = DatasetClass.objects.values('class_name').distinct().count()
    
    context = {
        'total_datasets': total_datasets,
        'completed_datasets': completed_datasets,
        'processing_datasets': processing_datasets,
        'failed_datasets': failed_datasets,
        'recent_datasets': recent_datasets,
        'total_images': total_images,
        'total_classes': total_classes,
        'page_title': 'Admin Dashboard'
    }
    
    return render(request, 'admin_dashboard/home.html', context)


