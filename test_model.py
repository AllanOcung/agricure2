"""
Test the trained model with sample images
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agricure.settings')
django.setup()

from dashboard.ai_service import AIService
from ai_models.crop_disease_model import CropDiseaseModel
import random

def test_model_predictions():
    """Test the trained model with sample images from each class"""
    
    print("🧪 TESTING TRAINED MODEL")
    print("=" * 60)
    
    # Initialize AI service
    ai_service = AIService()
    
    # Test dataset path
    dataset_path = Path("training_data")
    
    if not dataset_path.exists():
        print("❌ Training data not found!")
        return
    
    # Test images from each class
    for class_dir in sorted(dataset_path.iterdir()):
        if not class_dir.is_dir():
            continue
            
        class_name = class_dir.name
        print(f"\n📂 Testing class: {class_name}")
        print("-" * 40)
        
        # Get random sample images from this class
        image_files = [f for f in class_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png'}]
        
        if not image_files:
            print("  No images found in this class")
            continue
            
        # Test with 3 random images from each class
        sample_images = random.sample(image_files, min(3, len(image_files)))
        
        for i, image_path in enumerate(sample_images, 1):
            print(f"\n  Sample {i}: {image_path.name}")
            
            try:
                # Load model if not already loaded
                model_path = "ai_models/trained_models/tomato_v2.0_improved"
                if not hasattr(ai_service, 'model') or ai_service.model is None:
                    ai_service.model = CropDiseaseModel(model_path)
                
                # Make prediction
                result = ai_service.model.predict(str(image_path))
                
                # Display results
                print(f"    🔍 Predicted: {result['detected_disease']}")
                print(f"    📊 Confidence: {result['confidence_score']:.1f}%")
                print(f"    🚨 Severity: {result['severity']}")
                print(f"    🕒 Processing time: {result['processing_time']:.3f}s")
                
                # Check if prediction matches actual class
                predicted_disease = result['detected_disease'].lower()
                actual_class = class_name.lower()
                
                if actual_class in predicted_disease or predicted_disease in actual_class:
                    print(f"    ✅ CORRECT prediction!")
                else:
                    print(f"    ❌ INCORRECT prediction (should be {class_name})")
                    
            except Exception as e:
                print(f"    ❌ Error processing image: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 Model testing completed!")

def show_model_info():
    """Show information about the trained model"""
    
    print("📋 MODEL INFORMATION")
    print("=" * 60)
    
    model_path = Path("ai_models/trained_models/tomato_v2.0_improved")
    
    if not model_path.exists():
        print("❌ Trained model not found!")
        return
    
    # Check for metadata file
    metadata_file = model_path / "metadata.json"
    if metadata_file.exists():
        import json
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        print(f"Model version: {metadata.get('model_version', 'Unknown')}")
        print(f"Classes: {len(metadata.get('class_names', []))}")
        print(f"Class names: {', '.join(metadata.get('class_names', []))}")
        print(f"Input shape: {metadata.get('input_shape', 'Unknown')}")
        print(f"Created: {metadata.get('created_at', 'Unknown')}")
    else:
        print("⚠️ No metadata file found")
    
    # Check model file
    model_file = model_path / "model.h5"
    if model_file.exists():
        size_mb = model_file.stat().st_size / (1024 * 1024)
        print(f"Model file size: {size_mb:.1f} MB")
        print(f"Model file: {model_file}")
    else:
        print("❌ Model file not found!")

if __name__ == "__main__":
    # Show model information
    show_model_info()
    
    print("\n")
    
    # Test model predictions
    test_model_predictions()
