"""
NLP initialization utilities for setting up NLTK and other NLP resources
"""
from app.logging import get_logger

logger = get_logger(__name__)

# Import NLTK if available
try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer, ISRIStemmer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("NLTK is not available. NLP features will be limited.")

def init_nlp_resources(app_settings):
    """
    Initialize NLP resources and create an NLP client
    
    Args:
        app_settings: Application settings containing NLP configuration
        
    Returns:
        NLP client object or None if initialization fails
    """
    if not app_settings.NLP_ENABLED or not NLTK_AVAILABLE:
        if app_settings.NLP_ENABLED and not NLTK_AVAILABLE:
            logger.warning("NLP is enabled in settings but NLTK is not installed. Install with: pip install nltk")
        return None
        
    try:
        logger.info("Initializing NLTK resources")
        
        # Download necessary NLTK resources
        nltk_resources = [
            'punkt',              # For tokenization
            'stopwords',          # For stopwords
            'wordnet',            # For lemmatization
            'averaged_perceptron_tagger',  # For POS tagging
            'maxent_ne_chunker',  # For named entity recognition
            'words'               # For word lists
        ]
        
        # Note: The following Arabic resources are not available in NLTK's standard download:
        # - 'isri' (stemmer is available in code but not as a downloadable resource)
        # - 'arabic' (not a standard NLTK resource)
        # - 'arabic_punct' (not a standard NLTK resource)
        # - 'arabic_stopwords' (not a standard NLTK resource)
        # We'll handle Arabic processing with built-in NLTK components and custom lists
        
        for resource in nltk_resources:
            try:
                nltk.download(resource, quiet=True)
            except Exception as e:
                logger.warning(f"Failed to download NLTK resource {resource}: {e}")
        
        # Import our custom Arabic stopwords
        from app.utils.nltk_processor import ARABIC_STOPWORDS
        
        # Create a simple NLP client object with language-specific components
        nlp_client = {
            'tokenize': word_tokenize,
            'en_stemmer': PorterStemmer(),
            'ar_stemmer': ISRIStemmer(),
            'stopwords': {
                'en': set(stopwords.words('english')) if 'english' in stopwords._fileids else set(),
                # Use our comprehensive Arabic stopwords list
                'ar': ARABIC_STOPWORDS
            },
            'language': app_settings.PRIMARY_LANG
        }
        
        logger.info("NLTK resources loaded successfully")
        return nlp_client
        
    except Exception as e:
        logger.error(f"Failed to initialize NLTK: {e}")
        return None
