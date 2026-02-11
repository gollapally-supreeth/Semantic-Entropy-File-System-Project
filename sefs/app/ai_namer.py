import google.generativeai as genai
from .config import Config
import re

class AINamer:
    """
    Uses Google Gemini to generate descriptive folder names based on file content.
    """
    def __init__(self):
        self.cache = {}
        self.enabled = Config.USE_AI_NAMING and Config.GEMINI_API_KEY
        
        if self.enabled:
            try:
                genai.configure(api_key=Config.GEMINI_API_KEY)
                # Use models/ prefix for API compatibility
                model_name = f"models/{Config.GEMINI_MODEL}" if not Config.GEMINI_MODEL.startswith("models/") else Config.GEMINI_MODEL
                self.model = genai.GenerativeModel(model_name)
                print("✓ AI Naming Service: Enabled")
                print(f"  Model: {Config.GEMINI_MODEL}")
                print(f"  API Key: {Config.GEMINI_API_KEY[:20]}...")
            except Exception as e:
                print(f"✗ AI Naming Service: Failed to initialize")
                print(f"  Error: {e}")
                self.enabled = False
        else:
            if not Config.USE_AI_NAMING:
                print("AI Naming Service: Disabled (USE_AI_NAMING=False)")
            elif not Config.GEMINI_API_KEY:
                print("AI Naming Service: Disabled (no API key)")

    def generate_folder_name(self, text_samples, cluster_id):
        """
        Generates a descriptive folder name based on content.
        
        Args:
            text_samples: List of text strings (NOT file paths!)
            cluster_id: Fallback ID
            
        Returns:
            Descriptive folder name
        """
        if not self.enabled:
            return f"Semantic_Cluster_{cluster_id}"
        
        # Validate input
        if not text_samples or not isinstance(text_samples, list):
            print(f"WARNING: Invalid text_samples for cluster {cluster_id}")
            return f"Semantic_Cluster_{cluster_id}"
        
        # Filter out any file paths accidentally passed in
        valid_samples = []
        for sample in text_samples[:5]:
            if isinstance(sample, str) and len(sample) > 10:
                # Check if it looks like a file path (has backslash/forward slash)
                if '\\' not in sample and '/' not in sample:
                    valid_samples.append(sample[:500])
                elif len(sample) > 100:  # If it's long, might be actual content
                    valid_samples.append(sample[:500])
        
        if not valid_samples:
            print(f"WARNING: No valid text samples for cluster {cluster_id}")
            return f"Semantic_Cluster_{cluster_id}"
        
        # Create cache key
        cache_key = hash(tuple(valid_samples))
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            combined_text = "\n\n---\n\n".join(valid_samples)
            prompt = f"""Analyze these document excerpts and suggest ONE concise folder name (2-3 words max) that captures the main topic.

Documents:
{combined_text[:1500]}

Rules:
- Use underscore_case (e.g., Financial_Reports, Space_Research, Medical_Records)
- Be VERY specific and descriptive
- Maximum 3 words
- NO special characters except underscores
- NO file extensions
- Respond with ONLY the folder name, nothing else

Folder name:"""

            print(f"  Calling Gemini API...")
            response = self.model.generate_content(prompt)
            name = response.text.strip()
            print(f"  API Response: '{name}'")
            
            # Clean and validate
            name = self._sanitize_name(name)
            
            if name and len(name) > 2 and len(name) < 60:
                self.cache[cache_key] = name
                print(f"  ✓ AI Named: '{name}'")
                return name
            else:
                print(f"  ✗ Invalid AI response, using fallback")
                return f"Semantic_Cluster_{cluster_id}"
                
        except Exception as e:
            print(f"  ✗ AI Naming Error: {type(e).__name__}: {str(e)}")
            return f"Semantic_Cluster_{cluster_id}"
    
    def _sanitize_name(self, name):
        """Clean up AI-generated name"""
        # Remove quotes, extra spaces, newlines
        name = name.strip().strip('"').strip("'").strip('`')
        name = name.replace('\n', ' ').replace('\r', '')
        
        # Take only first line if multiple
        if '\n' in name:
            name = name.split('\n')[0]
        
        # Convert spaces/hyphens to underscores
        name = name.replace(' ', '_').replace('-', '_')
        
        # Remove any characters that aren't alphanumeric or underscore
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        
        # Capitalize each word
        parts = [p for p in name.split('_') if p]
        if not parts:
            return ""
        name = '_'.join(word.capitalize() for word in parts)
        
        # Limit length
        if len(name) > 50:
            name = '_'.join(name.split('_')[:3])  # Take first 3 words
            
        return name
