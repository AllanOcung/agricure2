"""
Quick test script to verify the improved model works
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agricure.settings')
django.setup()

# Add ai_models to path
sys.path.append(os.path.join(os.getcwd(), 'ai_models'))

try:
    from crop_disease_model import CropDiseaseModel
    print("✅ Successfully imported CropDiseaseModel")
    
    # Test loading the improved model
    model_path = "ai_models/trained_models/tomato_v2.0_improved"
    if os.path.exists(model_path):
        print(f"✅ Model directory exists: {model_path}")
        
        # Check for required files
        model_file = os.path.join(model_path, "model.h5")
        metadata_file = os.path.join(model_path, "metadata.json")
        
        print(f"Model file exists: {os.path.exists(model_file)}")
        print(f"Metadata file exists: {os.path.exists(metadata_file)}")
        
        if os.path.exists(model_file) and os.path.exists(metadata_file):
            try:
                # Load model
                model = CropDiseaseModel(model_path)
                print("✅ Model loaded successfully!")
                print(f"Model version: {model.model_version}")
                print(f"Class names: {model.class_names}")
                
                # Test with a sample image
                training_data = Path("training_data")
                if training_data.exists():
                    # Find first image
                    for class_dir in training_data.iterdir():
                        if class_dir.is_dir():
                            for img_file in class_dir.iterdir():
                                if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                                    print(f"\n🧪 Testing with: {img_file}")
                                    try:
                                        result = model.predict(str(img_file))
                                        print(f"Prediction: {result['detected_disease']}")
                                        print(f"Confidence: {result['confidence_score']:.1f}%")
                                        print(f"Severity: {result['severity']}")
                                        print("✅ Model prediction successful!")
                                    except Exception as e:
                                        print(f"❌ Prediction error: {e}")
                                    break
                            break
                else:
                    print("⚠️ No training data found for testing")
                    
            except Exception as e:
                print(f"❌ Error loading model: {e}")
        else:
            print("❌ Required model files not found")
    else:
        print(f"❌ Model directory not found: {model_path}")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n🎯 Model verification completed!")
