"""Random voice description generator for voice design examples."""

import random
from typing import List


def generate_random_voice_descriptions(count: int = 25) -> List[str]:
    """Generate random voice descriptions for voice design examples.
    
    Args:
        count: Number of descriptions to generate (default: 25)
        
    Returns:
        List of randomly generated voice description strings
    """
    # Gender options
    genders = ["male", "female"]
    
    # Age ranges
    ages = [
        "Teen",
        "Young",
        "Middle-aged",
        "Mature",
        "Elderly"
    ]
    
    # Ethnicities and nationalities
    ethnicities = [
        "Asian",
        "African American",
        "Caucasian",
        "Hispanic",
        "Latino",
        "Latina",
        "Middle Eastern",
        "Indian",
        "European",
        "African",
        "Brazilian",
        "Korean",
        "Japanese",
        "Chinese",
        "Irish",
        "Scottish",
        "Australian",
        "Canadian",
        "German",
        "French",
        "Italian",
        "Russian",
        "British",
        "American",
        "Mexican",
        "Spanish",
        "Portuguese",
        "Dutch",
        "Swedish",
        "Norwegian"
    ]
    
    # Emotional qualities
    emotions = [
        "cheerful",
        "melancholic",
        "anxious",
        "confident",
        "passionate",
        "calm",
        "excited",
        "tired",
        "angry",
        "joyful",
        "sad",
        "neutral",
        "mysterious",
        "optimistic",
        "pessimistic",
        "enthusiastic",
        "bored",
        "surprised",
        "warm",
        "cold",
        "friendly",
        "distant",
        "energetic",
        "lethargic",
        "hopeful",
        "desperate",
        "playful",
        "serious"
    ]
    
    # Speaking styles
    styles = [
        "professional",
        "casual",
        "formal",
        "conversational",
        "theatrical",
        "monotone",
        "dramatic",
        "deadpan",
        "animated",
        "reserved",
        "flamboyant",
        "humble",
        "boastful",
        "sarcastic",
        "sincere",
        "whimsical",
        "authoritative",
        "gentle",
        "aggressive",
        "passive",
        "assertive",
        "timid",
        "bold",
        "cautious"
    ]
    
    # Careers and archetypes
    careers = [
        "teacher",
        "engineer",
        "CEO",
        "athlete",
        "artist",
        "comedian",
        "doctor",
        "narrator",
        "podcaster",
        "therapist",
        "professor",
        "news anchor",
        "YouTuber",
        "salesperson",
        "storyteller",
        "motivational speaker",
        "customer service representative",
        "voice actor",
        "radio host",
        "DJ",
        "scientist",
        "politician",
        "preacher",
        "life coach",
        "meditation guide",
        "audiobook reader",
        "sports commentator",
        "game show host",
        "tour guide",
        "receptionist",
        "call center agent",
        "broadcaster",
        "announcer",
        "lecturer",
        "trainer",
        "consultant"
    ]
    
    # Vocal qualities
    vocal_qualities = [
        "clear articulation",
        "gravitas",
        "crisp pronunciation",
        "rising inflections",
        "meditative pacing",
        "vocal fry",
        "raspy tone",
        "breathy quality",
        "smooth delivery",
        "husky timbre",
        "nasal resonance",
        "deep resonance",
        "gravelly texture",
        "silky smoothness",
        "sharp enunciation",
        "flowing cadence",
        "staccato rhythm",
        "melodic intonation",
        "authoritative bass",
        "bright timbre",
        "mellow warmth",
        "crisp consonants",
        "rich overtones",
        "powerful projection",
        "gentle whisper",
        "booming presence",
        "lilting accent",
        "rhythmic phrasing",
        "commanding presence",
        "soothing tones"
    ]
    
    descriptions = []
    
    # Generate unique combinations
    for _ in range(count):
        age = random.choice(ages)
        ethnicity = random.choice(ethnicities)
        gender = random.choice(genders)
        emotion = random.choice(emotions)
        style = random.choice(styles)
        career = random.choice(careers)
        vocal_quality = random.choice(vocal_qualities)
        
        # Adjust ethnicity/gender combinations for natural language
        # (e.g., "Latina" should be with "female", "Latino" with "male")
        if ethnicity == "Latina" and gender == "male":
            ethnicity = "Latino"
        elif ethnicity == "Latino" and gender == "female":
            ethnicity = "Latina"
        
        description = (
            f"{age} {ethnicity} {gender} voice, "
            f"{emotion} and {style}, "
            f"{career} with {vocal_quality}"
        )
        
        descriptions.append(description)
    
    return descriptions


def generate_single_voice_description() -> str:
    """Generate a single random voice description.
    
    Returns:
        A randomly generated voice description string
    """
    return generate_random_voice_descriptions(count=1)[0]
