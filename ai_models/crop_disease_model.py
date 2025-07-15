"""
AI Model Training and Inference Module for Crop Disease Detection
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from PIL import Image
import cv2
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import joblib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CropDiseaseModel:
    """
    Main class for crop disease detection model
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the model
        
        Args:
            model_path: Path to saved model (if loading existing model)
        """
        self.model = None
        self.class_names = []
        self.input_shape = (224, 224, 3)  # Standard input shape
        self.model_version = "v1.0"
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def create_model(self, num_classes: int, input_shape: Tuple[int, int, int] = (224, 224, 3)) -> keras.Model:
        """
        Create a CNN model for crop disease classification
        
        Args:
            num_classes: Number of disease classes (including healthy)
            input_shape: Input image shape
            
        Returns:
            Compiled Keras model
        """
        self.input_shape = input_shape
        
        # Base model using transfer learning (MobileNetV2)
        base_model = keras.applications.MobileNetV2(
            input_shape=input_shape,
            include_top=False,
            weights='imagenet'
        )
        
        # Freeze base model layers initially
        base_model.trainable = False
        
        # Create complete model with enhanced regularization
        model = keras.Sequential([
            base_model,
            layers.GlobalAveragePooling2D(),
            layers.BatchNormalization(),        # Added batch normalization
            layers.Dropout(0.3),                # Increased dropout
            layers.Dense(256, activation='relu'), # Increased neurons
            layers.BatchNormalization(),        # Added batch normalization
            layers.Dropout(0.4),                # Higher dropout
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(num_classes, activation='softmax')
        ])
        
        # Compile model
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        self.model = model
        logger.info(f"Model created with {num_classes} classes")
        return model
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for model prediction
        
        Args:
            image_path: Path to image file
            
        Returns:
            Preprocessed image array
        """
        try:
            # Load and resize image
            image = Image.open(image_path).convert('RGB')
            image = image.resize((self.input_shape[0], self.input_shape[1]))
            
            # Convert to array and normalize
            image_array = np.array(image) / 255.0
            
            # Add batch dimension
            image_array = np.expand_dims(image_array, axis=0)
            
            return image_array
            
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {str(e)}")
            raise
    
    def predict(self, image_path: str) -> Dict:
        """
        Predict disease from crop image
        
        Args:
            image_path: Path to crop image
            
        Returns:
            Dictionary with prediction results
        """
        if self.model is None:
            raise ValueError("Model not loaded. Please load or train a model first.")
        
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            # Make prediction
            start_time = datetime.now()
            predictions = self.model.predict(processed_image, verbose=0)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Get prediction results
            predicted_class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_idx]) * 100
            
            # Get top 3 predictions
            top_indices = np.argsort(predictions[0])[-3:][::-1]
            top_predictions = []
            
            for idx in top_indices:
                top_predictions.append({
                    'disease': self.class_names[idx] if idx < len(self.class_names) else f'Class_{idx}',
                    'confidence': float(predictions[0][idx]) * 100
                })
            
            # Determine if diseased (assuming 'healthy' is first class)
            is_diseased = predicted_class_idx != 0 if self.class_names and 'healthy' in self.class_names[0].lower() else confidence > 50
            
            # Determine severity based on confidence
            severity = self._determine_severity(confidence, is_diseased)
            
            result = {
                'is_diseased': is_diseased,
                'detected_disease': self.class_names[predicted_class_idx] if predicted_class_idx < len(self.class_names) else f'Class_{predicted_class_idx}',
                'confidence_score': confidence,
                'severity': severity,
                'processing_time': processing_time,
                'alternative_diseases': top_predictions[1:],  # Exclude top prediction
                'model_version': self.model_version
            }
            
            logger.info(f"Prediction completed: {result['detected_disease']} ({confidence:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            raise
    
    def _determine_severity(self, confidence: float, is_diseased: bool) -> str:
        """
        Determine severity based on confidence and disease status
        """
        if not is_diseased:
            return 'healthy'
        
        if confidence >= 90:
            return 'critical'
        elif confidence >= 75:
            return 'high'
        elif confidence >= 60:
            return 'medium'
        else:
            return 'low'
    
    def save_model(self, save_path: str, class_names: List[str]):
        """
        Save trained model and metadata
        
        Args:
            save_path: Directory to save model
            class_names: List of class names
        """
        if self.model is None:
            raise ValueError("No model to save")
        
        os.makedirs(save_path, exist_ok=True)
        
        # Save model
        model_file = os.path.join(save_path, 'model.h5')
        self.model.save(model_file)
        
        # Save metadata
        metadata = {
            'class_names': class_names,
            'input_shape': self.input_shape,
            'model_version': self.model_version,
            'created_at': datetime.now().isoformat()
        }
        
        metadata_file = os.path.join(save_path, 'metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.class_names = class_names
        logger.info(f"Model saved to {save_path}")
    
    def load_model(self, model_path: str):
        """
        Load saved model and metadata
        
        Args:
            model_path: Path to saved model directory
        """
        try:
            # Load model
            model_file = os.path.join(model_path, 'model.h5')
            if os.path.exists(model_file):
                self.model = keras.models.load_model(model_file)
                logger.info(f"Model loaded from {model_file}")
            
            # Load metadata
            metadata_file = os.path.join(model_path, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                self.class_names = metadata.get('class_names', [])
                self.input_shape = tuple(metadata.get('input_shape', (224, 224, 3)))
                self.model_version = metadata.get('model_version', 'v1.0')
                
                logger.info(f"Metadata loaded: {len(self.class_names)} classes")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

class DatasetManager:
    """
    Manages training dataset for crop disease detection
    """
    
    def __init__(self, dataset_path: str):
        """
        Initialize dataset manager
        
        Args:
            dataset_path: Path to dataset directory
        """
        self.dataset_path = dataset_path
        self.class_names = []
    
    def organize_dataset(self, train_split: float = 0.8, val_split: float = 0.1):
        """
        Organize dataset into train/validation/test splits
        
        Args:
            train_split: Proportion for training
            val_split: Proportion for validation (rest goes to test)
        """
        # Implementation for organizing your dataset
        # This will depend on your dataset structure
        pass
    
    def create_data_generators(self, batch_size: int = 32, input_shape: Tuple[int, int] = (224, 224)):
        """
        Create data generators for training
        
        Args:
            batch_size: Batch size for training
            input_shape: Input image shape (height, width)
            
        Returns:
            Tuple of (train_generator, validation_generator, test_generator)
        """
        # Enhanced data augmentation for training with more variety
        train_datagen = keras.preprocessing.image.ImageDataGenerator(
            rescale=1./255,
            rotation_range=25,
            width_shift_range=0.2,
            height_shift_range=0.2,
            horizontal_flip=True,
            vertical_flip=True,          # Added for plant images
            zoom_range=0.2,
            shear_range=0.15,
            brightness_range=[0.8, 1.2], # Added brightness variation
            fill_mode='nearest',
            validation_split=0.25        # Increased validation split
        )
        
        # No augmentation for validation/test
        val_datagen = keras.preprocessing.image.ImageDataGenerator(
            rescale=1./255,
            validation_split=0.25
        )
        
        # Create generators
        train_generator = train_datagen.flow_from_directory(
            self.dataset_path,
            target_size=input_shape,
            batch_size=batch_size,
            class_mode='categorical',
            subset='training'
        )
        
        validation_generator = val_datagen.flow_from_directory(
            self.dataset_path,
            target_size=input_shape,
            batch_size=batch_size,
            class_mode='categorical',
            subset='validation'
        )
        
        self.class_names = list(train_generator.class_indices.keys())
        logger.info(f"Found {len(self.class_names)} classes: {self.class_names}")
        
        return train_generator, validation_generator

def train_model(dataset_path: str, model_save_path: str, epochs: int = 20, batch_size: int = 32) -> Dict:
    """
    Train crop disease detection model
    
    Args:
        dataset_path: Path to training dataset
        model_save_path: Path to save trained model
        epochs: Number of training epochs
        batch_size: Training batch size
        
    Returns:
        Training history and metrics
    """
    logger.info("Starting model training...")
    
    # Initialize components
    dataset_manager = DatasetManager(dataset_path)
    model = CropDiseaseModel()
    
    # Create data generators
    train_gen, val_gen = dataset_manager.create_data_generators(batch_size=batch_size)
    
    # Create model
    num_classes = len(dataset_manager.class_names)
    model.create_model(num_classes=num_classes)
    
    # Calculate class weights to handle imbalanced dataset
    from sklearn.utils.class_weight import compute_class_weight
    import numpy as np
    
    # Get class distribution from training generator
    class_indices = train_gen.class_indices
    classes = np.arange(len(class_indices))
    
    # Compute class weights
    class_weights = compute_class_weight(
        'balanced',
        classes=classes,
        y=train_gen.classes
    )
    class_weight_dict = dict(zip(classes, class_weights))
    
    logger.info(f"Class weights calculated for imbalanced dataset: {class_weight_dict}")
    
    # Training callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.2,
            patience=3
        ),
        keras.callbacks.ModelCheckpoint(
            filepath=os.path.join(model_save_path, 'best_model.h5'),
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        )
    ]
    
    # Train model with class weights
    start_time = datetime.now()
    history = model.model.fit(
        train_gen,
        epochs=epochs,
        validation_data=val_gen,
        callbacks=callbacks,
        class_weight=class_weight_dict,  # Handle imbalanced dataset
        verbose=1
    )
    training_duration = datetime.now() - start_time
    
    # Save model
    model.save_model(model_save_path, dataset_manager.class_names)
    
    # Prepare training results
    final_train_acc = max(history.history['accuracy'])
    final_val_acc = max(history.history['val_accuracy'])
    
    results = {
        'training_accuracy': final_train_acc,
        'validation_accuracy': final_val_acc,
        'training_duration': training_duration,
        'epochs_completed': len(history.history['accuracy']),
        'dataset_size': train_gen.samples,
        'class_names': dataset_manager.class_names,
        'class_weights': class_weight_dict
    }
    
    logger.info(f"Training completed! Validation accuracy: {final_val_acc:.4f}")
    return results
