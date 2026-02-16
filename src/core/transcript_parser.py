"""Transcript parsing for narration with voice assignment."""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from utils.error_handler import logger


@dataclass
class TranscriptSegment:
    """A segment of transcript with voice assignment."""
    text: str
    voice: Optional[str] = None
    segment_id: int = 0


class TranscriptParser:
    """Parse transcripts for multi-voice narration."""
    
    # Sentence-ending punctuation pattern
    SENTENCE_PATTERN = re.compile(
        r'([^.!?]+[.!?]+[\'")\]]*(?:\s|$))',
        re.UNICODE
    )
    
    # Speaker annotation patterns
    # Matches: [Speaker: Name], [Name], (Name), Name:
    SPEAKER_PATTERN = re.compile(
        r'(?:\[(?:Speaker:\s*)?([^\]]+)\]|\(([^)]+)\)|^([A-Za-z][A-Za-z\s]+):)',
        re.UNICODE | re.MULTILINE
    )
    
    def __init__(self):
        """Initialize transcript parser."""
        pass
    
    def parse_transcript(
        self,
        text: str,
        mode: str = "single",
        default_voice: Optional[str] = None
    ) -> List[TranscriptSegment]:
        """Parse transcript into segments based on mode.
        
        Args:
            text: Transcript text
            mode: Parsing mode ('single', 'manual', 'annotated', 'paragraphs')
            default_voice: Default voice for segments without assignment
            
        Returns:
            List of TranscriptSegment objects
        """
        if not text or not text.strip():
            logger.warning("parse_transcript called with empty text")
            return []
        
        logger.debug(f"Parsing transcript in {mode} mode, text length: {len(text)}")
        
        if mode == "single":
            return self._parse_single(text, default_voice)
        elif mode == "manual":
            return self._parse_manual(text)
        elif mode == "annotated":
            return self._parse_annotated(text, default_voice)
        elif mode == "paragraphs":
            return self._parse_paragraphs(text)
        else:
            raise ValueError(f"Unknown parsing mode: {mode}")
    
    def _parse_single(self, text: str, voice: Optional[str]) -> List[TranscriptSegment]:
        """Parse entire text as single segment.
        
        Args:
            text: Transcript text
            voice: Voice to assign
            
        Returns:
            List with single segment
        """
        logger.debug(f"Parsing as single segment with voice: {voice}")
        return [TranscriptSegment(text=text.strip(), voice=voice, segment_id=0)]
    
    def _parse_manual(self, text: str) -> List[TranscriptSegment]:
        """Parse text into segments by blank lines for manual voice assignment.
        
        Segments are separated by blank lines (double newlines). Text within a segment
        can span multiple lines, but a blank line creates a new segment.
        
        Args:
            text: Transcript text
            
        Returns:
            List of segments (one per text block separated by blank lines)
        """
        logger.debug("Splitting text into segments by blank lines...")
        segments = []
        
        # Split by blank lines (one or more consecutive newlines with optional whitespace)
        # This regex matches: newline, optional whitespace, newline (handles \n\n or \r\n\r\n)
        blocks = re.split(r'\n\s*\n', text)
        
        logger.debug(f"Found {len(blocks)} text blocks")
        
        for i, block in enumerate(blocks):
            # Strip whitespace but preserve internal line breaks
            cleaned_block = block.strip()
            if cleaned_block:
                segments.append(TranscriptSegment(
                    text=cleaned_block,
                    voice=None,
                    segment_id=i
                ))
        
        logger.info(f"Parsed {len(segments)} segments for manual assignment")
        return segments
    
    def _parse_annotated(
        self,
        text: str,
        default_voice: Optional[str]
    ) -> List[TranscriptSegment]:
        """Parse text with speaker annotations.
        
        Supports formats:
        - [Speaker: Name] Text here
        - [Name] Text here
        - (Name) Text here
        - Name: Text here (at start of line)
        
        Args:
            text: Annotated transcript text
            default_voice: Default voice when no speaker specified
            
        Returns:
            List of segments with voice assignments
        """
        segments = []
        current_voice = default_voice
        segment_id = 0
        
        # Split text into lines for processing
        lines = text.split('\n')
        current_text = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for speaker annotation at start of line
            match = self.SPEAKER_PATTERN.match(line)
            
            if match:
                # Save previous segment if exists
                if current_text:
                    text_content = ' '.join(current_text).strip()
                    if text_content:
                        segments.append(TranscriptSegment(
                            text=text_content,
                            voice=current_voice,
                            segment_id=segment_id
                        ))
                        segment_id += 1
                    current_text = []
                
                # Extract speaker name (check all capture groups)
                speaker = match.group(1) or match.group(2) or match.group(3)
                current_voice = speaker.strip()
                
                # Remove speaker annotation from line
                remaining_text = line[match.end():].strip()
                if remaining_text:
                    current_text.append(remaining_text)
            else:
                # Regular text line
                current_text.append(line)
        
        # Add final segment
        if current_text:
            text_content = ' '.join(current_text).strip()
            if text_content:
                segments.append(TranscriptSegment(
                    text=text_content,
                    voice=current_voice,
                    segment_id=segment_id
                ))
        
        logger.info(f"Parsed {len(segments)} annotated segments")
        return segments
    
    def _parse_paragraphs(self, text: str) -> List[TranscriptSegment]:
        """Parse text into paragraphs.
        
        Args:
            text: Transcript text
            
        Returns:
            List of segments (one per paragraph)
        """
        segments = []
        paragraphs = text.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if paragraph:
                segments.append(TranscriptSegment(
                    text=paragraph,
                    voice=None,
                    segment_id=i
                ))
        
        logger.info(f"Parsed {len(segments)} paragraphs")
        return segments
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Use regex to find sentence boundaries
        sentences = self.SENTENCE_PATTERN.findall(text)
        
        if not sentences:
            # Fallback: split on basic punctuation
            sentences = re.split(r'[.!?]+', text)
        
        return [s.strip() for s in sentences if s.strip()]
    
    def detect_speakers(self, text: str) -> List[str]:
        """Detect speaker names from annotated text.
        
        Args:
            text: Annotated transcript text
            
        Returns:
            List of unique speaker names found
        """
        speakers = set()
        
        for match in self.SPEAKER_PATTERN.finditer(text):
            speaker = match.group(1) or match.group(2) or match.group(3)
            if speaker:
                speakers.add(speaker.strip())
        
        result = sorted(list(speakers))
        logger.info(f"Detected speakers: {result}")
        return result
    
    def get_statistics(self, text: str) -> Dict[str, int]:
        """Get statistics about transcript text.
        
        Args:
            text: Transcript text
            
        Returns:
            Dictionary with statistics
        """
        words = text.split()
        sentences = self._split_into_sentences(text)
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        characters = len(text)
        
        return {
            "characters": characters,
            "words": len(words),
            "sentences": len(sentences),
            "paragraphs": len(paragraphs)
        }
    
    def validate_segment_voices(
        self,
        segments: List[TranscriptSegment],
        available_voices: List[str]
    ) -> Tuple[bool, List[str]]:
        """Validate that all segment voices are available.
        
        Args:
            segments: List of transcript segments
            available_voices: List of available voice names
            
        Returns:
            Tuple of (all_valid, list_of_missing_voices)
        """
        missing_voices = set()
        
        for segment in segments:
            if segment.voice and segment.voice not in available_voices:
                missing_voices.add(segment.voice)
        
        return len(missing_voices) == 0, sorted(list(missing_voices))
    
    def assign_voices_to_segments(
        self,
        segments: List[TranscriptSegment],
        voice_mapping: Dict[int, str]
    ) -> List[TranscriptSegment]:
        """Assign voices to segments based on mapping.
        
        Args:
            segments: List of transcript segments
            voice_mapping: Dictionary mapping segment_id to voice name
            
        Returns:
            Updated list of segments
        """
        for segment in segments:
            if segment.segment_id in voice_mapping:
                segment.voice = voice_mapping[segment.segment_id]
        
        return segments
    
    def load_transcript_file(self, filepath: str) -> str:
        """Load transcript from text file.
        
        Args:
            filepath: Path to transcript file
            
        Returns:
            Transcript text
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            logger.info(f"Loaded transcript from: {filepath}")
            return text
        except UnicodeDecodeError:
            # Try with different encoding
            with open(filepath, 'r', encoding='latin-1') as f:
                text = f.read()
            logger.info(f"Loaded transcript from: {filepath} (latin-1 encoding)")
            return text
        except Exception as e:
            logger.error(f"Failed to load transcript: {e}")
            raise
    
    def preview_segment(self, segment: TranscriptSegment, max_length: int = 80) -> str:
        """Generate preview text for a segment.
        
        Args:
            segment: Transcript segment
            max_length: Maximum preview length
            
        Returns:
            Preview string
        """
        text = segment.text
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        
        voice_info = f"[{segment.voice}] " if segment.voice else ""
        return f"{voice_info}{text}"
