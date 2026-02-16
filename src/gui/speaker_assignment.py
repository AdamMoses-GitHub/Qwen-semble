"""Speaker assignment panel for annotated narration mode."""

import customtkinter as ctk
from typing import Dict, Callable, List, Optional
from utils.error_handler import logger
from utils.theme import get_theme_colors
from gui.voice_browser import VoiceBrowserWidget


class SpeakerAssignmentPanel(ctk.CTkFrame):
    """Panel for assigning voices to detected speakers."""
    
    def __init__(
        self,
        parent,
        voice_library,
        tts_engine,
        config,
        speakers: List[str],
        segment_counts: Optional[Dict[str, int]] = None,
        on_assignment_change: Optional[Callable[[str, dict], None]] = None
    ):
        """
        Initialize speaker assignment panel.
        
        Args:
            parent: Parent widget
            voice_library: Voice library instance
            tts_engine: TTS engine instance
            config: Config instance
            speakers: List of detected speaker names
            segment_counts: Dictionary mapping speaker names to segment counts
            on_assignment_change: Callback(speaker_name, voice_data) when assignment changes
        """
        super().__init__(parent)
        
        self.voice_library = voice_library
        self.tts_engine = tts_engine
        self.config = config
        self.speakers = speakers
        self.segment_counts = segment_counts or {}
        self.on_assignment_change = on_assignment_change
        
        # Storage for speaker-to-voice assignments
        self.speaker_assignments: Dict[str, dict] = {}
        
        # Speaker color mapping for visual identification
        self.speaker_colors = self._generate_speaker_colors()
        
        self._create_ui()
    
    def _generate_speaker_colors(self) -> Dict[str, str]:
        """Generate distinct colors for each speaker."""
        colors = [
            "#3b82f6",  # blue
            "#ec4899",  # pink
            "#10b981",  # green
            "#f59e0b",  # amber
            "#8b5cf6",  # violet
            "#ef4444",  # red
            "#14b8a6",  # teal
            "#f97316",  # orange
        ]
        
        color_map = {}
        for i, speaker in enumerate(self.speakers):
            color_map[speaker] = colors[i % len(colors)]
        
        return color_map
    
    def _create_ui(self) -> None:
        """Create the speaker assignment table UI."""
        self.columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            self,
            text="Speaker Voice Assignment",
            font=("Arial", 14, "bold")
        )
        title.grid(row=0, column=0, pady=(5, 10), sticky="w", padx=10)
        
        # Info text
        info = ctk.CTkLabel(
            self,
            text="Assign a voice to each detected speaker",
            text_color="gray",
            font=("Arial", 11)
        )
        info.grid(row=1, column=0, pady=(0, 10), sticky="w", padx=10)
        
        # Scrollable frame for speaker rows (no headers)
        self.rows_frame = ctk.CTkScrollableFrame(self, height=300)
        self.rows_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.rows_frame.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        
        # Create rows for each speaker
        self.speaker_rows = {}
        for i, speaker in enumerate(self.speakers):
            row = self._create_speaker_row(speaker, i)
            self.speaker_rows[speaker] = row
        
        # Validation status
        self.validation_label = ctk.CTkLabel(
            self,
            text="",
            text_color="orange",
            font=("Arial", 11)
        )
        self.validation_label.grid(row=3, column=0, pady=(5, 10), padx=10)
        
        self._update_validation_status()
    
    def _create_speaker_row(self, speaker: str, row_index: int) -> Dict:
        """Create a 2x2 grid for a single speaker."""
        # Main container frame for this speaker
        row_frame = ctk.CTkFrame(self.rows_frame, border_width=1)
        row_frame.grid(row=row_index, column=0, sticky="ew", pady=5, padx=5)
        
        # Configure 2x2 grid
        row_frame.columnconfigure(0, weight=1)  # Left column
        row_frame.columnconfigure(1, weight=1)  # Right column
        row_frame.rowconfigure(0, weight=0)     # Top row
        row_frame.rowconfigure(1, weight=0)     # Bottom row
        
        # Get speaker color and theme colors
        color = self.speaker_colors[speaker]
        colors = get_theme_colors()
        
        # Upper left: Speaker name/number with colored text and position indicator
        speaker_number = row_index + 1
        total_speakers = len(self.speakers)
        speaker_text = f"({speaker_number} of {total_speakers}) {speaker}"
        speaker_label = ctk.CTkLabel(
            row_frame,
            text=speaker_text,
            font=("Arial", 13, "bold"),
            text_color=color,
            anchor="w"
        )
        speaker_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
        
        # Upper right: Segment count
        count = self.segment_counts.get(speaker, 0)
        count_label = ctk.CTkLabel(
            row_frame,
            text=f"{count} segments",
            font=("Arial", 11),
            text_color=colors["text_secondary"],
            anchor="e"
        )
        count_label.grid(row=0, column=1, sticky="e", padx=10, pady=(8, 4))
        
        # Lower left: Assigned voice or "Not assigned"
        voice_label = ctk.CTkLabel(
            row_frame,
            text="Not assigned",
            font=("Arial", 11),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        voice_label.grid(row=1, column=0, sticky="w", padx=10, pady=(4, 8))
        
        # Lower right: Select Voice button
        browse_button = ctk.CTkButton(
            row_frame,
            text="Select Voice",
            width=120,
            command=lambda s=speaker: self._browse_voice_for_speaker(s)
        )
        browse_button.grid(row=1, column=1, sticky="e", padx=10, pady=(4, 8))
        
        return {
            'frame': row_frame,
            'speaker_label': speaker_label,
            'count_label': count_label,
            'voice_label': voice_label,
            'browse_button': browse_button
        }
    
    def _browse_voice_for_speaker(self, speaker: str) -> None:
        """Open voice browser for a specific speaker."""
        logger.debug(f"Opening voice browser for speaker: {speaker}")
        
        def on_voice_select(voice_data: dict) -> None:
            self._on_voice_assigned(speaker, voice_data)
        
        browser = VoiceBrowserWidget(
            self,
            voice_library=self.voice_library,
            tts_engine=self.tts_engine,
            config=self.config,
            on_select=on_voice_select
        )
        browser.wait_window()
    
    def _on_voice_assigned(self, speaker: str, voice_data: dict) -> None:
        """Handle voice assignment to a speaker."""
        self.speaker_assignments[speaker] = voice_data
        colors = get_theme_colors()
        
        # Update the UI
        voice_name = voice_data['name']
        voice_type = voice_data.get('type', 'preset')
        display_text = f"{voice_name} ({voice_type})"
        
        row = self.speaker_rows[speaker]
        row['voice_label'].configure(text=display_text, text_color=colors["text_primary"])
        
        # Update validation status
        self._update_validation_status()
        
        # Call callback if provided
        if self.on_assignment_change:
            self.on_assignment_change(speaker, voice_data)
        
        logger.info(f"Assigned voice '{voice_name}' to speaker '{speaker}'")
    
    def _update_validation_status(self) -> None:
        """Update validation status message."""
        colors = get_theme_colors()
        assigned_count = len(self.speaker_assignments)
        total_count = len(self.speakers)
        
        if assigned_count == 0:
            self.validation_label.configure(
                text="⚠️ No voices assigned yet",
                text_color=colors["warning_text"]
            )
        elif assigned_count < total_count:
            remaining = total_count - assigned_count
            self.validation_label.configure(
                text=f"⚠️ {remaining} speaker(s) still need voice assignment",
                text_color=colors["warning_text"]
            )
        else:
            self.validation_label.configure(
                text="✅ All speakers have voices assigned",
                text_color=colors["success_text"]
            )
    
    def get_assignments(self) -> Dict[str, dict]:
        """
        Get all speaker-to-voice assignments.
        
        Returns:
            Dictionary mapping speaker names to voice data dictionaries
        """
        return self.speaker_assignments.copy()
    
    def is_complete(self) -> bool:
        """Check if all speakers have voices assigned."""
        return len(self.speaker_assignments) == len(self.speakers)
    
    def set_assignment(self, speaker: str, voice_data: dict) -> None:
        """
        Programmatically set a voice assignment for a speaker.
        
        Args:
            speaker: Speaker name
            voice_data: Voice data dictionary
        """
        if speaker not in self.speakers:
            logger.warning(f"Attempted to assign voice to unknown speaker: {speaker}")
            return
        
        self._on_voice_assigned(speaker, voice_data)
    
    def clear_assignments(self) -> None:
        """Clear all voice assignments."""
        self.speaker_assignments.clear()
        colors = get_theme_colors()
        
        for speaker, row in self.speaker_rows.items():
            row['voice_label'].configure(text="Not assigned", text_color=colors["text_secondary"])
        
        self._update_validation_status()
        logger.info("Cleared all speaker voice assignments")
    
    def get_speaker_color(self, speaker: str) -> str:
        """Get the color assigned to a speaker."""
        return self.speaker_colors.get(speaker, "#808080")
