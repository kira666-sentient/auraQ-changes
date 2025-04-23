import joblib
import pandas as pd
import os
from pathlib import Path
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# Define file path to the dataset
DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'emoDATASET', 'text.csv')
print(f"Looking for dataset at: {DATASET_PATH}")

# Emotion mapping for the dataset (numeric to text)
EMOTION_MAP = {
    0: "sadness",
    1: "joy",
    2: "love",
    3: "anger",
    4: "fear",
    5: "surprise"
}

# Check if the dataset exists
if not os.path.exists(DATASET_PATH):
    print(f"❌ Error: Dataset not found at {DATASET_PATH}")
    print("Using sample data instead...")
    # Sample training data as fallback
    training_texts = ["I am happy today", "I feel so sad", "This is amazing", "I am angry", "I love this day"]
    training_labels = ["joy", "sadness", "joy", "anger", "joy"]
    
    # Convert text to feature vectors
    vectorizer = CountVectorizer()
    X_train = vectorizer.fit_transform(training_texts)
    
    # Train model
    model = MultinomialNB()
    model.fit(X_train, training_labels)
else:
    print(f"✅ Found dataset at {DATASET_PATH}")
    
    try:
        # Load dataset
        print("Loading and processing dataset...")
        df = pd.read_csv(DATASET_PATH)
        
        # Display info about the dataset
        print(f"Dataset shape: {df.shape}")
        print("Column names:", df.columns.tolist())
        print("Sample data:")
        print(df.head(3))
        
        # Identify text and label columns
        # Assuming the CSV has columns 'text' and 'label' or similar
        text_column = next((col for col in df.columns if 'text' in col.lower()), df.columns[0])
        label_column = next((col for col in df.columns if 'label' in col.lower() or 'emotion' in col.lower()), df.columns[1])
        
        print(f"Using '{text_column}' as text column and '{label_column}' as label column")
        
        # Extract texts and labels
        texts = df[text_column].astype(str).tolist()
        numeric_labels = df[label_column].tolist()
        
        # Convert numeric labels to text labels based on the emotion map
        labels = []
        for label in numeric_labels:
            # Try to convert to int if it's not already
            try:
                label_idx = int(label)
                if label_idx in EMOTION_MAP:
                    labels.append(EMOTION_MAP[label_idx])
                else:
                    labels.append("neutral")  # Default for unknown labels
            except (ValueError, TypeError):
                # If conversion fails, use the original label
                labels.append(str(label))
        
        print(f"Total samples: {len(texts)}")
        print(f"Emotion distribution: {pd.Series(labels).value_counts().to_dict()}")
        
        # Split data into training and testing sets (80% training, 20% testing)
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        print(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")
        
        # Convert text to feature vectors using TF-IDF (better than CountVectorizer for text classification)
        print("Vectorizing texts...")
        vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=3)
        X_train_vec = vectorizer.fit_transform(X_train)
        X_test_vec = vectorizer.transform(X_test)
        
        # Train model
        print("Training Naive Bayes model...")
        model = MultinomialNB(alpha=0.1)  # Slightly reduce smoothing for better specificity
        model.fit(X_train_vec, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_vec)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Model accuracy: {accuracy:.2f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Print top features for each emotion
        print("\nTop features for each emotion:")
        feature_names = vectorizer.get_feature_names_out()
        for i, emotion in enumerate(model.classes_):
            top_features_idx = model.feature_log_prob_[i].argsort()[-10:]
            top_features = [feature_names[idx] for idx in top_features_idx]
            print(f"{emotion}: {', '.join(top_features)}")
        
    except Exception as e:
        print(f"❌ Error processing dataset: {str(e)}")
        print("Using sample data instead...")
        # Sample training data as fallback
        training_texts = ["I am happy today", "I feel so sad", "This is amazing", "I am angry", "I love this day"]
        training_labels = ["joy", "sadness", "joy", "anger", "joy"]
        
        # Convert text to feature vectors
        vectorizer = CountVectorizer()
        X_train = vectorizer.fit_transform(training_texts)
        
        # Train model
        model = MultinomialNB()
        model.fit(X_train, training_labels)

# Save model and vectorizer
output_dir = os.path.dirname(__file__)
model_path = os.path.join(output_dir, "emotion_model.pkl")
vectorizer_path = os.path.join(output_dir, "vectorizer.pkl")

joblib.dump(model, model_path)
joblib.dump(vectorizer, vectorizer_path)

print(f"✅ Model saved to: {model_path}")
print(f"✅ Vectorizer saved to: {vectorizer_path}")
print("✅ Training completed successfully!")
