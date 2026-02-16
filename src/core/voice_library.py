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
    
    def __init__(self, library_path: str = "config/voice_library.json", workspace_dir: Optional[Path] = None):
        """Initialize voice library.
        
        Args:
            library_path: Path to voice library JSON file (relative to workspace if workspace_dir provided)
            workspace_dir: Root workspace directory (if None, uses old structure)
        """
        self.workspace_dir = workspace_dir
        
        # Resolve paths based on workspace mode
        if workspace_dir:
            self.library_path = workspace_dir / "voice_library.json"
            self.cloned_voices_dir = workspace_dir / "cloned_voices"
            self.designed_voices_dir = workspace_dir / "designed_voices"
        else:
            self.library_path = Path(library_path)
            self.cloned_voices_dir = Path("output/cloned_voices")
            self.designed_voices_dir = Path("output/designed_voices")
        
        self.library: Dict[str, List[Dict]] = {
            "preset_voices": [],
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
                # Ensure preset_voices section exists
                if "preset_voices" not in self.library:
                    self.library["preset_voices"] = []
                logger.info(f"Voice library loaded: {len(self.library.get('preset_voices', []))} preset, {len(self.library['cloned_voices'])} cloned, {len(self.library['designed_voices'])} designed")
            else:
                self.save()
        except Exception as e:
            logger.error(f"Error loading voice library: {e}")
            self.library = {"preset_voices": [], "cloned_voices": [], "designed_voices": []}
    
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
    
    def _create_readme(self, voice_data: Dict, voice_folder: Path) -> None:
        """Create a README.txt file with voice metadata.
        
        Args:
            voice_data: Dictionary containing voice metadata
            voice_folder: Path to voice folder
        """
        try:
            readme_path = voice_folder / "README.txt"
            
            # Format creation date
            created_date = datetime.fromisoformat(voice_data["created"])
            formatted_date = created_date.strftime("%B %d, %Y at %I:%M %p")
            
            # Build readme content
            content = []
            content.append("=" * 70)
            content.append(f"VOICE MODEL: {voice_data['name']}")
            content.append("=" * 70)
            content.append("")
            
            # Basic details
            content.append("BASIC DETAILS")
            content.append("-" * 70)
            content.append(f"Voice ID:       {voice_data['id']}")
            content.append(f"Type:           {voice_data['type'].capitalize()}")
            content.append(f"Created:        {formatted_date}")
            content.append(f"Language:       {voice_data.get('language', 'Auto')}")
            
            # Tags
            if voice_data.get('tags'):
                tags_str = ", ".join(voice_data['tags'])
                content.append(f"Tags:           {tags_str}")
            else:
                content.append("Tags:           None")
            content.append("")
            
            # Type-specific details
            if voice_data['type'] == 'cloned':
                content.append("CLONED VOICE DETAILS")
                content.append("-" * 70)
                content.append(f"Reference Audio: {Path(voice_data['ref_audio']).name}")
                content.append("")
                content.append("Reference Text:")
                # Wrap reference text at 68 characters
                ref_text = voice_data.get('ref_text', 'N/A')
                words = ref_text.split()
                line = ""
                for word in words:
                    if len(line) + len(word) + 1 <= 68:
                        line += (" " if line else "") + word
                    else:
                        content.append(f"  {line}")
                        line = word
                if line:
                    content.append(f"  {line}")
                content.append("")
                content.append(f"Voice Prompt:    {Path(voice_data['prompt_file']).name}")
                
            elif voice_data['type'] == 'designed':
                content.append("DESIGNED VOICE DETAILS")
                content.append("-" * 70)
                content.append(f"Sample Audio:    {Path(voice_data['sample_audio']).name}")
                content.append("")
                content.append("Voice Description:")
                # Wrap description text at 68 characters
                description = voice_data.get('description', 'N/A')
                words = description.split()
                line = ""
                for word in words:
                    if len(line) + len(word) + 1 <= 68:
                        line += (" " if line else "") + word
                    else:
                        content.append(f"  {line}")
                        line = word
                if line:
                    content.append(f"  {line}")
            
            content.append("")
            
            # Template tests
            if voice_data.get('template_tests'):
                content.append("TEMPLATE TEST AUDIO FILES")
                content.append("-" * 70)
                for idx, test_path in enumerate(voice_data['template_tests'], 1):
                    content.append(f"  {idx}. {Path(test_path).name}")
                content.append("")
            
            # Usage statistics
            content.append("USAGE STATISTICS")
            content.append("-" * 70)
            content.append(f"Times Used:     {voice_data.get('usage_count', 0)}")
            last_used = voice_data.get('last_used')
            if last_used:
                last_used_date = datetime.fromisoformat(last_used)
                formatted_last_used = last_used_date.strftime("%B %d, %Y at %I:%M %p")
                content.append(f"Last Used:      {formatted_last_used}")
            else:
                content.append("Last Used:      Never")
            content.append("")
            
            # Footer
            content.append("=" * 70)
            content.append("This voice model was created with Qwen-semble.")
            content.append("For more information, see the voice_library.json file.")
            content.append("=" * 70)
            
            # Write to file
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(content))
            
            logger.debug(f"Created README.txt in {voice_folder.name}")
            
        except Exception as e:
            logger.error(f"Failed to create README.txt: {e}")
            # Don't raise - readme is supplementary, not critical
    
    def save_cloned_voice(
        self,
        name: str,
        ref_audio_path: str,
        ref_text: str,
        voice_clone_prompt: Any,
        tags: Optional[List[str]] = None,
        language: str = "Auto",
        template_test_audios: Optional[Dict[int, tuple]] = None,
        custom_test_audios: Optional[List[Dict]] = None
    ) -> str:
        """Save a cloned voice to library.
        
        Args:
            name: Display name for the voice
            ref_audio_path: Path to reference audio file
            ref_text: Reference transcript
            voice_clone_prompt: Voice clone prompt object
            tags: Optional tags for categorization
            language: Voice language
            template_test_audios: Dict of {index: (audio_array, sample_rate)} for template tests
            custom_test_audios: List of dicts with {text, audio_path, audio, sr} for custom tests
            
        Returns:
            Voice ID
        """
        try:
            from core.audio_utils import save_audio
            
            logger.info(f"Saving cloned voice: {name}")
            voice_id = self._generate_voice_id("cloned")
            logger.debug(f"Generated voice ID: {voice_id}")
            
            # Create timestamped subfolder: VoiceName_YYYYMMDD_HHMMSS
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize name for folder
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name)
            safe_name = safe_name.replace(' ', '_')
            folder_name = f"{safe_name}_{timestamp}"
            voice_folder = self.cloned_voices_dir / folder_name
            voice_folder.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created voice folder: {voice_folder}")
            
            # Copy audio file to subfolder
            audio_dest = voice_folder / "reference.wav"
            logger.debug(f"Copying reference audio to: {audio_dest}")
            shutil.copy2(ref_audio_path, audio_dest)
            
            # Save voice clone prompt
            prompt_dest = voice_folder / "voice_prompt.pkl"
            logger.debug(f"Saving voice clone prompt to: {prompt_dest}")
            with open(prompt_dest, 'wb') as f:
                pickle.dump(voice_clone_prompt, f)
            
            # Save template test audios if provided
            template_test_paths = []
            if template_test_audios:
                logger.debug(f"Saving {len(template_test_audios)} template test audios...")
                for idx in sorted(template_test_audios.keys()):
                    audio, sr = template_test_audios[idx]
                    test_path = voice_folder / f"template_test_{idx+1}.wav"
                    save_audio(audio, sr, str(test_path))
                    template_test_paths.append(str(test_path))
                    logger.debug(f"Saved template test {idx+1}")
            
            # Save custom test audios if provided
            custom_test_data = []
            if custom_test_audios:
                logger.debug(f"Saving {len(custom_test_audios)} custom test audios...")
                for idx, custom_test in enumerate(custom_test_audios):
                    # Copy the audio file to voice folder
                    test_path = voice_folder / f"custom_test_{idx+1}.wav"
                    shutil.copy2(custom_test["audio_path"], test_path)
                    custom_test_data.append({
                        "text": custom_test["text"],
                        "audio_path": str(test_path)
                    })
                    logger.debug(f"Saved custom test {idx+1}: {custom_test['text'][:50]}...")
            
            # Create metadata
            voice_data = {
                "id": voice_id,
                "name": name,
                "tags": tags or [],
                "type": "cloned",
                "created": datetime.now().isoformat(),
                "folder": str(voice_folder),
                "ref_audio": str(audio_dest),
                "ref_text": ref_text,
                "prompt_file": str(prompt_dest),
                "language": language,
                "template_tests": template_test_paths,
                "custom_tests": custom_test_data,
                "usage_count": 0,
                "last_used": None
            }
            
            logger.debug("Adding voice to library and saving...")
            self.library["cloned_voices"].append(voice_data)
            self.save()
            
            # Create README.txt with voice details
            self._create_readme(voice_data, voice_folder)
            
            logger.info(f"Cloned voice saved: {name} ({voice_id}) in folder: {folder_name}")
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
        language: str = "Auto",
        template_test_audios: Optional[Dict[int, tuple]] = None,
        custom_test_audios: Optional[List[Dict]] = None
    ) -> str:
        """Save a designed voice to library.
        
        Args:
            name: Display name for the voice
            description: Voice description used for design
            sample_audio_path: Path to sample audio file
            tags: Optional tags for categorization
            language: Voice language
            template_test_audios: Dict of {index: (audio_array, sample_rate)} for template tests
            custom_test_audios: List of dicts with {text, audio_path, audio, sr} for custom tests
            
        Returns:
            Voice ID
        """
        try:
            from core.audio_utils import save_audio
            
            logger.info(f"Saving designed voice: {name}")
            voice_id = self._generate_voice_id("designed")
            logger.debug(f"Generated voice ID: {voice_id}")
            
            # Create timestamped subfolder: VoiceName_YYYYMMDD_HHMMSS
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize name for folder
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name)
            safe_name = safe_name.replace(' ', '_')
            folder_name = f"{safe_name}_{timestamp}"
            voice_folder = self.designed_voices_dir / folder_name
            voice_folder.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created voice folder: {voice_folder}")
            
            # Copy sample audio file to subfolder
            audio_dest = voice_folder / "sample.wav"
            logger.debug(f"Copying sample audio to: {audio_dest}")
            shutil.copy2(sample_audio_path, audio_dest)
            
            # Save template test audios if provided
            template_test_paths = []
            if template_test_audios:
                logger.debug(f"Saving {len(template_test_audios)} template test audios...")
                for idx in sorted(template_test_audios.keys()):
                    audio, sr = template_test_audios[idx]
                    test_path = voice_folder / f"template_test_{idx+1}.wav"
                    save_audio(audio, sr, str(test_path))
                    template_test_paths.append(str(test_path))
                    logger.debug(f"Saved template test {idx+1}")
            
            # Save custom test audios if provided
            custom_test_data = []
            if custom_test_audios:
                logger.debug(f"Saving {len(custom_test_audios)} custom test audios...")
                for idx, custom_test in enumerate(custom_test_audios):
                    # Copy the audio file to voice folder
                    test_path = voice_folder / f"custom_test_{idx+1}.wav"
                    shutil.copy2(custom_test["audio_path"], test_path)
                    custom_test_data.append({
                        "text": custom_test["text"],
                        "audio_path": str(test_path)
                    })
                    logger.debug(f"Saved custom test {idx+1}: {custom_test['text'][:50]}...")
            
            # Create metadata
            voice_data = {
                "id": voice_id,
                "name": name,
                "tags": tags or [],
                "type": "designed",
                "created": datetime.now().isoformat(),
                "folder": str(voice_folder),
                "description": description,
                "sample_audio": str(audio_dest),
                "language": language,
                "template_tests": template_test_paths,
                "custom_tests": custom_test_data,
                "usage_count": 0,
                "last_used": None
            }
            
            self.library["designed_voices"].append(voice_data)
            self.save()
            
            # Create README.txt with voice details
            self._create_readme(voice_data, voice_folder)
            
            logger.info(f"Designed voice saved: {name} ({voice_id}) in folder: {folder_name}")
            return voice_id
            
        except Exception as e:
            logger.error(f"Failed to save designed voice: {e}")
            raise
    
    def get_all_voices(self, voice_type: Optional[str] = None) -> List[Dict]:
        """Get all voices or voices of specific type.
        
        Args:
            voice_type: Optional filter ('cloned', 'designed', or 'preset')
            
        Returns:
            List of voice data dictionaries
        """
        if voice_type == "cloned":
            return self.library["cloned_voices"].copy()
        elif voice_type == "designed":
            return self.library["designed_voices"].copy()
        elif voice_type == "preset":
            return self.library.get("preset_voices", []).copy()
        else:
            # Return all voices
            preset_voices = self.library.get("preset_voices", [])
            return preset_voices + self.library["cloned_voices"] + self.library["designed_voices"]
    
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
    
    def increment_usage(self, voice_id: str) -> bool:
        """Increment usage count for a voice.
        
        Args:
            voice_id: Voice ID
            
        Returns:
            True if successful, False if voice not found
        """
        try:
            # Find the voice in either list
            voice = None
            voice_list = None
            
            for v in self.library["cloned_voices"]:
                if v["id"] == voice_id:
                    voice = v
                    voice_list = "cloned_voices"
                    break
            
            if not voice:
                for v in self.library["designed_voices"]:
                    if v["id"] == voice_id:
                        voice = v
                        voice_list = "designed_voices"
                        break
            
            if not voice:
                logger.warning(f"Voice not found for usage tracking: {voice_id}")
                return False
            
            # Update usage stats (with backward compatibility)
            if "usage_count" not in voice:
                voice["usage_count"] = 0
            voice["usage_count"] += 1
            voice["last_used"] = datetime.now().isoformat()
            
            # Save changes
            self.save()
            logger.debug(f"Updated usage for voice {voice_id}: {voice['usage_count']} uses")
            return True
            
        except Exception as e:
            logger.error(f"Failed to increment usage for {voice_id}: {e}")
            return False
    
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
    
    def import_preset_voices(self, tts_engine) -> int:
        """Auto-import engine preset voices to library on first launch.
        
        Args:
            tts_engine: TTSEngine instance to get supported speakers
            
        Returns:
            Number of presets imported
        """
        # Get speaker info from engine
        speakers_info = tts_engine.SPEAKERS
        
        # Add preset_voices section if it doesn't exist
        if "preset_voices" not in self.library:
            self.library["preset_voices"] = []
        
        imported_count = 0
        
        for speaker_info in speakers_info:
            speaker_name = speaker_info["name"]
            voice_id = f"preset_{speaker_name.lower()}"
            
            # Check if already imported
            if any(v.get("id") == voice_id for v in self.library["preset_voices"]):
                continue
            
            # Add to library
            preset_voice = {
                "id": voice_id,
                "name": speaker_name,
                "type": "preset",
                "preset_name": speaker_name,
                "language": speaker_info.get("language", "Multi"),
                "description": speaker_info.get("description", ""),
                "tags": ["preset", "built-in"],
                "created": datetime.now().isoformat(),
                "usage_count": 0
            }
            
            self.library["preset_voices"].append(preset_voice)
            imported_count += 1
            logger.debug(f"Imported preset voice: {speaker_name}")
        
        if imported_count > 0:
            self.save()
            logger.info(f"Imported {imported_count} preset voices to library")
        
        return imported_count
