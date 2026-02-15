"""Voice library management for saving and loading voices."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import pickle
import shutil

from utils.error_handler import logger


class VoiceLibrary:
    """Manage saved cloned and designed voices."""
    
    def __init__(self, library_path: str = "config/voice_library.json"):
        """Initialize voice library.
        
        Args:
            library_path: Path to voice library JSON file
        """
        self.library_path = Path(library_path)
        self.cloned_voices_dir = Path("output/cloned_voices")
        self.designed_voices_dir = Path("output/designed_voices")
        self.library: Dict[str, List[Dict]] = {
            "cloned_voices": [],
            "designed_voices": []
        }
        
        # Ensure directories exist
        self.cloned_voices_dir.mkdir(parents=True, exist_ok=True)
        self.designed_voices_dir.mkdir(parents=True, exist_ok=True)
        
        self.load()
    
    def load(self) -> None:
        """Load voice library from file."""
        try:
            if self.library_path.exists():
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    self.library = json.load(f)
                logger.info(f"Voice library loaded: {len(self.library['cloned_voices'])} cloned, {len(self.library['designed_voices'])} designed")
            else:
                self.save()
        except Exception as e:
            logger.error(f"Error loading voice library: {e}")
            self.library = {"cloned_voices": [], "designed_voices": []}
    
    def save(self) -> None:
        """Save voice library to file."""
        try:
            self.library_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.library_path, 'w', encoding='utf-8') as f:
                json.dump(self.library, f, indent=2)
            logger.info("Voice library saved")
        except Exception as e:
            logger.error(f"Error saving voice library: {e}")
    
    def _generate_voice_id(self, voice_type: str) -> str:
        """Generate unique voice ID.
        
        Args:
            voice_type: 'cloned' or 'designed'
            
        Returns:
            Unique voice ID
        """
        voices = self.library.get(f"{voice_type}_voices", [])
        existing_ids = [v["id"] for v in voices]
        
        counter = 1
        while True:
            voice_id = f"{voice_type}_{counter:03d}"
            if voice_id not in existing_ids:
                return voice_id
            counter += 1
    
    def save_cloned_voice(
        self,
        name: str,
        ref_audio_path: str,
        ref_text: str,
        voice_clone_prompt: Any,
        tags: Optional[List[str]] = None,
        language: str = "Auto"
    ) -> str:
        """Save a cloned voice to library.
        
        Args:
            name: Display name for the voice
            ref_audio_path: Path to reference audio file
            ref_text: Reference transcript
            voice_clone_prompt: Voice clone prompt object
            tags: Optional tags for categorization
            language: Voice language
            
        Returns:
            Voice ID
        """
        try:
            logger.info(f"Saving cloned voice: {name}")
            voice_id = self._generate_voice_id("cloned")
            logger.debug(f"Generated voice ID: {voice_id}")
            
            # Copy audio file to library
            audio_dest = self.cloned_voices_dir / f"{voice_id}.wav"
            logger.debug(f"Copying reference audio to: {audio_dest}")
            shutil.copy2(ref_audio_path, audio_dest)
            
            # Save voice clone prompt
            prompt_dest = self.cloned_voices_dir / f"{voice_id}_prompt.pkl"
            logger.debug(f"Saving voice clone prompt to: {prompt_dest}")
            with open(prompt_dest, 'wb') as f:
                pickle.dump(voice_clone_prompt, f)
            
            # Create metadata
            voice_data = {
                "id": voice_id,
                "name": name,
                "tags": tags or [],
                "type": "cloned",
                "created": datetime.now().isoformat(),
                "ref_audio": str(audio_dest),
                "ref_text": ref_text,
                "prompt_file": str(prompt_dest),
                "language": language
            }
            
            logger.debug("Adding voice to library and saving...")
            self.library["cloned_voices"].append(voice_data)
            self.save()
            
            logger.info(f"Cloned voice saved: {name} ({voice_id})")
            return voice_id
            
        except Exception as e:
            logger.error(f"Failed to save cloned voice: {e}")
            raise
    
    def save_designed_voice(
        self,
        name: str,
        description: str,
        sample_audio_path: str,
        tags: Optional[List[str]] = None,
        language: str = "Auto"
    ) -> str:
        """Save a designed voice to library.
        
        Args:
            name: Display name for the voice
            description: Voice description used for design
            sample_audio_path: Path to sample audio file
            tags: Optional tags for categorization
            language: Voice language
            
        Returns:
            Voice ID
        """
        try:
            voice_id = self._generate_voice_id("designed")
            
            # Copy audio file to library
            audio_dest = self.designed_voices_dir / f"{voice_id}.wav"
            shutil.copy2(sample_audio_path, audio_dest)
            
            # Create metadata
            voice_data = {
                "id": voice_id,
                "name": name,
                "tags": tags or [],
                "type": "designed",
                "created": datetime.now().isoformat(),
                "description": description,
                "sample_audio": str(audio_dest),
                "language": language
            }
            
            self.library["designed_voices"].append(voice_data)
            self.save()
            
            logger.info(f"Designed voice saved: {name} ({voice_id})")
            return voice_id
            
        except Exception as e:
            logger.error(f"Failed to save designed voice: {e}")
            raise
    
    def get_all_voices(self, voice_type: Optional[str] = None) -> List[Dict]:
        """Get all voices or voices of specific type.
        
        Args:
            voice_type: Optional filter ('cloned' or 'designed')
            
        Returns:
            List of voice data dictionaries
        """
        if voice_type == "cloned":
            return self.library["cloned_voices"].copy()
        elif voice_type == "designed":
            return self.library["designed_voices"].copy()
        else:
            # Return all voices
            return self.library["cloned_voices"] + self.library["designed_voices"]
    
    def get_voice(self, voice_id: str) -> Optional[Dict]:
        """Get voice data by ID.
        
        Args:
            voice_id: Voice ID
            
        Returns:
            Voice data dictionary or None if not found
        """
        all_voices = self.get_all_voices()
        for voice in all_voices:
            if voice["id"] == voice_id:
                return voice
        return None
    
    def get_voice_by_name(self, name: str) -> Optional[Dict]:
        """Get voice data by name.
        
        Args:
            name: Voice name (can include '[Library] ' prefix)
            
        Returns:
            Voice data dictionary or None if not found
        """
        # Strip [Library] prefix if present
        clean_name = name.replace("[Library] ", "").strip()
        
        all_voices = self.get_all_voices()
        for voice in all_voices:
            if voice["name"] == clean_name:
                return voice
        return None
    
    def load_voice_clone_prompt(self, voice_id: str) -> Any:
        """Load voice clone prompt for a cloned voice.
        
        Args:
            voice_id: Voice ID
            
        Returns:
            Voice clone prompt object
        """
        voice = self.get_voice(voice_id)
        if not voice or voice["type"] != "cloned":
            raise ValueError(f"Cloned voice not found: {voice_id}")
        
        prompt_file = Path(voice["prompt_file"])
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, 'rb') as f:
            return pickle.load(f)
    
    def delete_voice(self, voice_id: str) -> bool:
        """Delete voice from library.
        
        Args:
            voice_id: Voice ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            voice = self.get_voice(voice_id)
            if not voice:
                return False
            
            # Remove from library
            voice_type = voice["type"]
            voices_key = f"{voice_type}_voices"
            self.library[voices_key] = [
                v for v in self.library[voices_key] if v["id"] != voice_id
            ]
            
            # Delete files
            if voice_type == "cloned":
                audio_file = Path(voice["ref_audio"])
                prompt_file = Path(voice["prompt_file"])
                if audio_file.exists():
                    audio_file.unlink()
                if prompt_file.exists():
                    prompt_file.unlink()
            else:  # designed
                audio_file = Path(voice["sample_audio"])
                if audio_file.exists():
                    audio_file.unlink()
            
            self.save()
            logger.info(f"Voice deleted: {voice_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete voice: {e}")
            return False
    
    def search_voices(
        self,
        query: str = "",
        tags: Optional[List[str]] = None,
        voice_type: Optional[str] = None
    ) -> List[Dict]:
        """Search voices by name, tags, or type.
        
        Args:
            query: Search query for name/description
            tags: Filter by tags
            voice_type: Filter by type ('cloned' or 'designed')
            
        Returns:
            List of matching voice data dictionaries
        """
        voices = self.get_all_voices(voice_type)
        results = []
        
        query_lower = query.lower()
        
        for voice in voices:
            # Check name match
            name_match = query_lower in voice["name"].lower() if query else True
            
            # Check description match (for designed voices)
            desc_match = False
            if "description" in voice:
                desc_match = query_lower in voice["description"].lower()
            
            # Check tags match
            tags_match = True
            if tags:
                voice_tags = set(voice.get("tags", []))
                tags_match = bool(voice_tags.intersection(tags))
            
            if (name_match or desc_match) and tags_match:
                results.append(voice)
        
        return results
    
    def get_voice_count(self, voice_type: Optional[str] = None) -> int:
        """Get count of voices in library.
        
        Args:
            voice_type: Optional filter ('cloned' or 'designed')
            
        Returns:
            Number of voices
        """
        return len(self.get_all_voices(voice_type))
    
    def export_voice(self, voice_id: str, export_path: str) -> None:
        """Export voice data to a file for sharing.
        
        Args:
            voice_id: Voice ID
            export_path: Path to export file
        """
        voice = self.get_voice(voice_id)
        if not voice:
            raise ValueError(f"Voice not found: {voice_id}")
        
        export_data = voice.copy()
        
        # Export audio and prompt files
        export_dir = Path(export_path).parent
        export_dir.mkdir(parents=True, exist_ok=True)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Voice exported: {voice_id} to {export_path}")
