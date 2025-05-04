"""
NLTK-based text processing utilities for English and Arabic
"""
import re
from typing import List, Dict, Any, Set
from app.logging import get_logger

logger = get_logger(__name__)

# Arabic diacritics (tashkeel) to be removed for normalization
ARABIC_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')

# Arabic letter variations mapping for normalization
ARABIC_LETTER_VARIATIONS = {
    'أ': 'ا',  # Alef with hamza above -> Alef
    'إ': 'ا',  # Alef with hamza below -> Alef
    'آ': 'ا',  # Alef with madda above -> Alef
    'ة': 'ه',  # Taa marbouta -> Haa
    'ى': 'ي',  # Alef maksura -> Yaa
    'ئ': 'ي',  # Yaa with hamza above -> Yaa
    'ؤ': 'و'   # Waw with hamza above -> Waw
}

# Comprehensive Arabic stopwords list since NLTK's Arabic stopwords might not be available
ARABIC_STOPWORDS = {
    # Pronouns
    'أنا', 'نحن', 'أنت', 'أنتم', 'أنتما', 'أنتن', 'هو', 'هي', 'هم', 'هما', 'هن',

    # Demonstratives
    'هذا', 'هذه', 'ذلك', 'تلك', 'هؤلاء', 'أولئك', 'هذان', 'هاتان', 'ذانك', 'تانك',

    # Relative pronouns
    'الذي', 'التي', 'الذين', 'اللذين', 'اللتين', 'اللذان', 'اللتان', 'اللاتي', 'اللائي',

    # Prepositions
    'من', 'إلى', 'عن', 'على', 'في', 'بـ', 'لـ', 'كـ', 'بين', 'قبل', 'بعد', 'تحت', 'فوق',
    'منذ', 'حول', 'حين', 'بينما', 'ضمن', 'عبر', 'مع', 'خلف', 'أمام', 'وراء',
    'لدى', 'عند', 'أثناء', 'خلال', 'طوال', 'ضد', 'حتى', 'إلا',

    # Conjunctions
    'و', 'أو', 'ثم', 'فـ', 'لكن', 'بل', 'لأن', 'إذا', 'إن', 'أن', 'كي', 'حتى',

    # Negations
    'لا', 'لم', 'لن', 'ما', 'ليس', 'غير',

    # Question words
    'من', 'ما', 'ماذا', 'متى', 'أين', 'كيف', 'لماذا', 'هل', 'أ',

    # Other common stopwords
    'بدون', 'دون', 'سوى', 'مثل', 'كمثل', 'أي', 'كل', 'بعض', 'غير', 'سوف', 'قد',
    'فقط', 'كان', 'كانت', 'يكون', 'تكون', 'أصبح', 'أصبحت', 'صار', 'صارت', 'أمسى', 'أمست',
    'ظل', 'ظلت', 'بات', 'باتت', 'مازال', 'مازالت', 'مادام', 'مادامت', 'ليس', 'ليست',
    'جدا', 'فقط', 'أبدا', 'دائما', 'أيضا', 'هنا', 'هناك'
}

def is_arabic_text(text: str) -> bool:
    """
    Check if text contains Arabic characters

    Args:
        text: The text to check

    Returns:
        True if text contains Arabic characters, False otherwise
    """
    # Arabic Unicode range
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')
    return bool(arabic_pattern.search(text))

def normalize_arabic_text(text: str) -> str:
    """
    Normalize Arabic text by:
    1. Removing diacritics (tashkeel)
    2. Normalizing letter variations
    3. Removing tatweel (kashida)

    Args:
        text: The Arabic text to normalize

    Returns:
        Normalized Arabic text
    """
    if not text:
        return text

    # Remove diacritics
    text = ARABIC_DIACRITICS.sub('', text)

    # Remove tatweel (kashida)
    text = text.replace('\u0640', '')

    # Normalize letter variations
    for original, replacement in ARABIC_LETTER_VARIATIONS.items():
        text = text.replace(original, replacement)

    return text

def clean_text(text: str, is_arabic: bool = False) -> str:
    """
    Clean text by removing special characters and normalizing

    Args:
        text: The text to clean
        is_arabic: Whether the text is Arabic

    Returns:
        Cleaned text
    """
    # Basic cleaning
    text = text.replace("\n", " ")

    if is_arabic:
        # Arabic-specific cleaning
        text = normalize_arabic_text(text)
        text = text.replace("؟", " ").replace("،", " ")
    else:
        # English/general cleaning
        text = text.replace("?", " ").replace(".", " ").replace(",", " ")

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def get_stopwords(nlp_client, language: str = 'en') -> Set[str]:
    """
    Get stopwords for the specified language

    Args:
        nlp_client: The NLP client with stopwords
        language: Language code ('en' or 'ar')

    Returns:
        Set of stopwords
    """
    if not nlp_client or 'stopwords' not in nlp_client:
        # Fallback to built-in lists if NLP client is not available
        if language == 'ar':
            return ARABIC_STOPWORDS
        return set()

    # Get language-specific stopwords
    if language == 'ar':
        # Start with any Arabic stopwords from NLTK (if available)
        stopwords = nlp_client['stopwords'].get('ar', set())
        # Add our comprehensive Arabic stopwords
        stopwords.update(ARABIC_STOPWORDS)
        return stopwords
    else:
        # Default to English
        return nlp_client['stopwords'].get('en', set())

def tokenize_text(text: str, nlp_client) -> List[str]:
    """
    Tokenize text into words

    Args:
        text: The text to tokenize
        nlp_client: The NLP client with tokenizer

    Returns:
        List of tokens
    """
    if not nlp_client or 'tokenize' not in nlp_client:
        # Simple fallback tokenization
        return text.split()

    # For Arabic text, use simple whitespace tokenization
    # This is more reliable for Arabic than NLTK's punkt tokenizer
    if is_arabic_text(text):
        # Arabic-specific tokenization
        # First normalize the text
        normalized = normalize_arabic_text(text)
        # Then split by whitespace
        tokens = normalized.split()
        return tokens

    try:
        # For non-Arabic text, use NLTK tokenizer
        return nlp_client['tokenize'](text)
    except Exception as e:
        logger.error(f"Error tokenizing text: {e}")
        # Fallback to simple splitting
        return text.split()

def stem_word(word: str, nlp_client, language: str = 'en') -> str:
    """
    Stem a word to its root form

    Args:
        word: The word to stem
        nlp_client: The NLP client with stemmers
        language: Language code ('en' or 'ar')

    Returns:
        Stemmed word
    """
    if not nlp_client:
        return word

    try:
        if language == 'ar' and 'ar_stemmer' in nlp_client:
            return nlp_client['ar_stemmer'].stem(word)
        elif 'en_stemmer' in nlp_client:
            return nlp_client['en_stemmer'].stem(word)
        else:
            return word
    except Exception as e:
        logger.error(f"Error stemming word '{word}': {e}")
        return word

def extract_keywords(text: str, nlp_client, language: str = None) -> List[str]:
    """
    Extract keywords from text

    Args:
        text: The text to process
        nlp_client: The NLP client
        language: Language code ('en' or 'ar')

    Returns:
        List of keywords
    """
    # Detect language if not specified
    if language is None:
        language = 'ar' if is_arabic_text(text) else 'en'

    # Clean the text
    clean = clean_text(text, is_arabic=(language == 'ar'))

    # If no NLP client, return cleaned text split by spaces
    if not nlp_client:
        logger.debug("NLP client not available, using basic keyword extraction")
        return clean.split()

    # Special handling for Arabic text
    if language == 'ar':
        # For Arabic, we'll use a more direct approach
        # First normalize the text
        normalized = normalize_arabic_text(clean)

        # Get Arabic stopwords
        stop_words = get_stopwords(nlp_client, 'ar')

        # Simple whitespace tokenization for Arabic
        tokens = normalized.split()

        # Filter out stopwords and short words
        keywords = [token for token in tokens if token not in stop_words and len(token) > 1]

        logger.debug(f"Extracted {len(keywords)} Arabic keywords: {', '.join(keywords[:10])}")
        return keywords

    # For non-Arabic languages (English, etc.)
    # Get stopwords for the language
    stop_words = get_stopwords(nlp_client, language)

    # Tokenize the text
    tokens = tokenize_text(clean, nlp_client)

    # Filter out stopwords and short words
    keywords = [token for token in tokens if token.lower() not in stop_words and len(token) > 1]

    # Stem keywords if needed (optional)
    # stemmed_keywords = [stem_word(word, nlp_client, language) for word in keywords]

    return keywords

def enhance_query(query: str, nlp_client, language: str = None) -> Dict[str, Any]:
    """
    Enhance a query for better search results

    Args:
        query: The query to enhance
        nlp_client: The NLP client
        language: Language code ('en' or 'ar')

    Returns:
        Dictionary with enhanced query information
    """
    # Detect language if not specified
    if language is None:
        language = 'ar' if is_arabic_text(query) else 'en'

    # Clean the query
    cleaned_query = clean_text(query, is_arabic=(language == 'ar'))

    # Extract keywords
    keywords = extract_keywords(cleaned_query, nlp_client, language)

    # Join keywords to form enhanced query
    enhanced_query = " ".join(keywords) if keywords else cleaned_query

    return {
        "original_query": query,
        "cleaned_query": cleaned_query,
        "enhanced_query": enhanced_query,
        "keywords": keywords,
        "language": language
    }
