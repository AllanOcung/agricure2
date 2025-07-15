"""
Enhanced Model Training with Better Regularization and Data Augmentation
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
from sklearn.utils.class_weight import compute_class_weight

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_enhanced_data_generators(dataset_path: str, batch_size: int = 32, input_shape: Tuple[int, int] = (224, 224)):
    """
    Create enhanced data generators with better augmentation to reduce overfitting
    """
    # Enhanced data augmentation for training
    train_datagen = keras.preprocessing.image.ImageDataGenerator(
        rescale=1./255,
        rotation_range=30,           # Increased rotation
        width_shift_range=0.25,      # Increased shift
        height_shift_range=0.25,     # Increased shift
        horizontal_flip=True,
        vertical_flip=True,          # Added vertical flip for plant images
        zoom_range=0.25,             # Increased zoom
        shear_range=0.15,            # Reduced shear (too much can distort plant features)
        brightness_range=[0.8, 1.2], # Added brightness variation
        fill_mode='nearest',
        validation_split=0.25        # Increased validation split for better evaluation
    )
    
    # Validation data - only rescaling
    val_datagen = keras.preprocessing.image.ImageDataGenerator(
        rescale=1./255,
        validation_split=0.25
    )
    
    # Create generators
    train_generator = train_datagen.flow_from_directory(
        dataset_path,
        target_size=input_shape,
        batch_size=batch_size,
        class_mode='categorical',
        subset='training',
        shuffle=True
    )
    
    validation_generator = val_datagen.flow_from_directory(
        dataset_path,
        target_size=input_shape,
        batch_size=batch_size,
        class_mode='categorical',
        subset='validation',
        shuffle=False
    )
    
    return train_generator, validation_generator

def create_enhanced_model(num_classes: int, input_shape: Tuple[int, int, int] = (224, 224, 3)) -> keras.Model:
    """
    Create an enhanced model with better regularization
    """
    # Base model with more layers unfrozen for fine-tuning
    base_model = keras.applications.MobileNetV2(
        input_shape=input_shape,
        include_top=False,
        weights='imagenet'
    )
    
    # Unfreeze the top layers of the base model for fine-tuning
    base_model.trainable = True
    
    # Fine-tune from this layer onwards
    fine_tune_at = 100
    
    # Freeze all the layers before the `fine_tune_at` layer
    for layer in base_model.layers[:fine_tune_at]:
        layer.trainable = False
    
    # Enhanced model architecture with better regularization
    model = keras.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.BatchNormalization(),              # Added batch normalization
        layers.Dropout(0.3),                      # Increased dropout
        layers.Dense(256, activation='relu'),      # Increased neurons
        layers.BatchNormalization(),              # Added batch normalization
        layers.Dropout(0.4),                      # Higher dropout for regularization
        layers.Dense(128, activation='relu'),      # Additional layer
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Dense(num_classes, activation='softmax')
    ])
    
    # Use a lower learning rate for fine-tuning
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),  # Lower learning rate
        loss='categorical_crossentropy',
        metrics=['accuracy']  # Standard accuracy metric
    )
    
    return model

def train_enhanced_model(dataset_path: str, model_save_path: str, epochs: int = 30, batch_size: int = 16) -> Dict:
    """
    Train enhanced model with better regularization and data augmentation
    """
    logger.info("Starting enhanced model training with better regularization...")
    
    # Create enhanced data generators
    train_gen, val_gen = create_enhanced_data_generators(dataset_path, batch_size=batch_size)
    
    # Get class names and calculate class weights
    class_names = list(train_gen.class_indices.keys())
    num_classes = len(class_names)
    
    # Calculate class weights for imbalanced dataset
    class_indices = train_gen.class_indices
    classes = np.arange(len(class_indices))
    class_weights = compute_class_weight(
        'balanced',
        classes=classes,
        y=train_gen.classes
    )
    class_weight_dict = dict(zip(classes, class_weights))
    logger.info(f"Class weights: {class_weight_dict}")
    
    # Create enhanced model
    model = create_enhanced_model(num_classes=num_classes)
    
    # Enhanced callbacks
    callbacks = [
        # Early stopping with more patience for fine-tuning
        keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=8,
            restore_best_weights=True,
            verbose=1
        ),
        
        # Reduce learning rate on plateau
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.3,
            patience=4,
            min_lr=1e-7,
            verbose=1
        ),
        
        # Model checkpoint
        keras.callbacks.ModelCheckpoint(
            filepath=os.path.join(model_save_path, 'best_enhanced_model.h5'),
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        ),
        
        # Learning rate scheduler for fine-tuning
        keras.callbacks.LearningRateScheduler(
            lambda epoch: 0.0001 * 0.95 ** epoch,  # Exponential decay
            verbose=0
        )
    ]
    
    # Create save directory
    os.makedirs(model_save_path, exist_ok=True)
    
    # Train model
    start_time = datetime.now()
    history = model.fit(
        train_gen,
        epochs=epochs,
        validation_data=val_gen,
        callbacks=callbacks,
        class_weight=class_weight_dict,
        verbose=1
    )
    training_duration = datetime.now() - start_time
    
    # Save model and metadata
    model.save(os.path.join(model_save_path, 'enhanced_model.h5'))
    
    # Save metadata
    metadata = {
        'class_names': class_names,
        'input_shape': (224, 224, 3),
        'model_version': 'enhanced_v1.0',
        'training_accuracy': max(history.history['accuracy']),
        'validation_accuracy': max(history.history['val_accuracy']),
        'training_duration': str(training_duration),
        'epochs_completed': len(history.history['accuracy']),
        'dataset_size': train_gen.samples,
        'class_weights': {str(k): float(v) for k, v in class_weight_dict.items()},
        'created_at': datetime.now().isoformat()
    }
    
    with open(os.path.join(model_save_path, 'enhanced_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Prepare results
    results = {
        'training_accuracy': max(history.history['accuracy']),
        'validation_accuracy': max(history.history['val_accuracy']),
        'training_duration': training_duration,
        'epochs_completed': len(history.history['accuracy']),
        'dataset_size': train_gen.samples,
        'class_names': class_names,
        'class_weights': class_weight_dict
    }
    
    logger.info(f"Enhanced training completed!")
    logger.info(f"Training accuracy: {results['training_accuracy']:.4f}")
    logger.info(f"Validation accuracy: {results['validation_accuracy']:.4f}")
    
    return results

if __name__ == "__main__":
    # Configuration
    DATASET_PATH = "training_data"
    MODEL_SAVE_PATH = "ai_models/trained_models/enhanced_tomato_v1.0"
    EPOCHS = 30
    BATCH_SIZE = 16
    
    print("🚀 ENHANCED MODEL TRAINING")
    print("=" * 60)
    print(f"Dataset: {DATASET_PATH}")
    print(f"Save path: {MODEL_SAVE_PATH}")
    print(f"Epochs: {EPOCHS}")
    print(f"Batch size: {BATCH_SIZE}")
    print("=" * 60)
    
    # Train enhanced model
    results = train_enhanced_model(
        dataset_path=DATASET_PATH,
        model_save_path=MODEL_SAVE_PATH,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE
    )
    
    print("\n🎯 ENHANCED TRAINING COMPLETED!")
    print("=" * 60)
    for key, value in results.items():
        if key != 'class_weights':
            print(f"{key}: {value}")
