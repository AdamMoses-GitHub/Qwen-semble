"""Reusable GUI components for the application."""

import customtkinter as ctk
from tkinter import filedialog
from typing import Optional, Callable, List
from pathlib import Path

from core.audio_utils import AudioPlayer
from utils.error_handler import logger


class AudioPlayerWidget(ctk.CTkFrame):
    """Widget for audio playback with controls."""
    
    def __init__(self, parent, **kwargs):
        """Initialize audio player widget.
        
        Args:
            parent: Parent widget
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)
        
        self.audio_player = AudioPlayer()
        self.current_audio = None
        self.current_sr = None
        
        # Create UI
        self.play_button = ctk.CTkButton(
            self,
            text="▶ Play",
            command=self._toggle_playback,
            width=100
        )
        self.play_button.pack(side="left", padx=5)
        
        self.status_label = ctk.CTkLabel(
            self,
            text="No audio loaded",
            width=200
        )
        self.status_label.pack(side="left", padx=5)
        
        self._update_ui()
    
    def load_audio(self, audio, sample_rate: int) -> None:
        """Load audio for playback.
        
        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
        """
        self.current_audio = audio
        self.current_sr = sample_rate
        duration = len(audio) / sample_rate
        self.status_label.configure(text=f"Ready ({duration:.1f}s)")
        self.play_button.configure(state="normal")
    
    def _toggle_playback(self) -> None:
        """Toggle play/stop."""
        if self.audio_player.is_playing():
            self.stop()
        else:
            self.play()
    
    def play(self) -> None:
        """Start playback."""
        if self.current_audio is not None and self.current_sr is not None:
            self.play_button.configure(text="⏸ Stop")
            self.status_label.configure(text="Playing...")
            self.audio_player.play(
                self.current_audio,
                self.current_sr,
                callback=self._on_playback_complete
            )
    
    def stop(self) -> None:
        """Stop playback."""
        self.audio_player.stop()
        self._on_playback_complete()
    
    def _on_playback_complete(self) -> None:
        """Handle playback completion."""
        self.play_button.configure(text="▶ Play")
        if self.current_audio is not None and self.current_sr is not None:
            duration = len(self.current_audio) / self.current_sr
            self.status_label.configure(text=f"Ready ({duration:.1f}s)")
    
    def _update_ui(self) -> None:
        """Update UI state."""
        if self.current_audio is None:
            self.play_button.configure(state="disabled")


class FilePickerWidget(ctk.CTkFrame):
    """Widget for selecting files with browse button."""
    
    def __init__(
        self,
        parent,
        label: str = "File:",
        filetypes: Optional[List[tuple]] = None,
        callback: Optional[Callable] = None,
        **kwargs
    ):
        """Initialize file picker widget.
        
        Args:
            parent: Parent widget
            label: Label text
            filetypes: File type filters for dialog
            callback: Function to call when file selected
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)
        
        self.filetypes = filetypes or [("All files", "*.*")]
        self.callback = callback
        self.selected_file = None
        
        # Label
        self.label = ctk.CTkLabel(self, text=label, width=80)
        self.label.pack(side="left", padx=5)
        
        # File path display
        self.path_label = ctk.CTkLabel(
            self,
            text="No file selected",
            width=300,
            anchor="w"
        )
        self.path_label.pack(side="left", padx=5, fill="x", expand=True)
        
        # Browse button
        self.browse_button = ctk.CTkButton(
            self,
            text="Browse...",
            command=self._browse,
            width=100
        )
        self.browse_button.pack(side="right", padx=5)
    
    def _browse(self) -> None:
        """Open file dialog."""
        filepath = filedialog.askopenfilename(
            title=f"Select {self.label.cget('text')}",
            filetypes=self.filetypes
        )
        
        if filepath:
            self.set_file(filepath)
    
    def set_file(self, filepath: str) -> None:
        """Set selected file.
        
        Args:
            filepath: Path to file
        """
        self.selected_file = filepath
        filename = Path(filepath).name
        self.path_label.configure(text=filename)
        
        if self.callback:
            self.callback(filepath)
    
    def get_file(self) -> Optional[str]:
        """Get selected file path.
        
        Returns:
            File path or None
        """
        return self.selected_file
    
    def clear(self) -> None:
        """Clear selected file."""
        self.selected_file = None
        self.path_label.configure(text="No file selected")


class VoiceLibraryItem(ctk.CTkFrame):
    """Widget for displaying a voice in the library."""
    
    def __init__(
        self,
        parent,
        voice_data: dict,
        on_load: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
        on_play: Optional[Callable] = None,
        **kwargs
    ):
        """Initialize voice library item.
        
        Args:
            parent: Parent widget
            voice_data: Voice metadata dictionary
            on_load: Callback when load button clicked
            on_delete: Callback when delete button clicked
            on_play: Callback when play button clicked
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)
        
        self.voice_data = voice_data
        self.on_load = on_load
        self.on_delete = on_delete
        self.on_play = on_play
        
        # Voice name and info
        name_text = voice_data.get("name", "Unknown")
        voice_type = voice_data.get("type", "")
        info_text = f"{name_text} ({voice_type})"
        
        self.name_label = ctk.CTkLabel(
            self,
            text=info_text,
            width=200,
            anchor="w"
        )
        self.name_label.pack(side="left", padx=5)
        
        # Tags
        tags = voice_data.get("tags", [])
        if tags:
            tags_text = ", ".join(tags[:3])  # Show first 3 tags
            self.tags_label = ctk.CTkLabel(
                self,
                text=f"[{tags_text}]",
                width=150,
                anchor="w",
                text_color="gray"
            )
            self.tags_label.pack(side="left", padx=5)
        
        # Buttons
        if on_play:
            self.play_button = ctk.CTkButton(
                self,
                text="▶",
                command=lambda: on_play(voice_data),
                width=40
            )
            self.play_button.pack(side="right", padx=2)
        
        if on_delete:
            self.delete_button = ctk.CTkButton(
                self,
                text="Delete",
                command=lambda: on_delete(voice_data),
                width=60,
                fg_color="darkred"
            )
            self.delete_button.pack(side="right", padx=2)
        
        if on_load:
            self.load_button = ctk.CTkButton(
                self,
                text="Load",
                command=lambda: on_load(voice_data),
                width=60
            )
            self.load_button.pack(side="right", padx=2)


class LoadingOverlay(ctk.CTkToplevel):
    """Modal loading dialog with progress indicator."""
    
    def __init__(self, parent, title: str = "Loading...", message: str = "Please wait..."):
        """Initialize loading overlay.
        
        Args:
            parent: Parent window
            title: Window title
            message: Loading message
        """
        super().__init__(parent)
        
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        # Message
        self.message_label = ctk.CTkLabel(
            self,
            text=message,
            font=("Arial", 14)
        )
        self.message_label.pack(pady=20)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # Status
        self.status_label = ctk.CTkLabel(
            self,
            text="Initializing...",
            font=("Arial", 10),
            text_color="gray"
        )
        self.status_label.pack(pady=5)
        
        # Center window
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def update_progress(self, percentage: float, message: str = "") -> None:
        """Update progress.
        
        Args:
            percentage: Progress percentage (0-100)
            message: Status message
        """
        self.progress_bar.set(percentage / 100.0)
        if message:
            self.status_label.configure(text=message)
        self.update()
    
    def close(self) -> None:
        """Close the overlay."""
        self.grab_release()
        self.destroy()


class SegmentListRow(ctk.CTkFrame):
    """Widget for displaying a transcript segment with voice selector."""
    
    def __init__(
        self,
        parent,
        segment_id: int,
        text_preview: str,
        voices: List[str],
        on_voice_change: Optional[Callable] = None,
        **kwargs
    ):
        """Initialize segment list row.
        
        Args:
            parent: Parent widget
            segment_id: Segment ID
            text_preview: Preview of segment text
            voices: Available voice options
            on_voice_change: Callback when voice selection changes
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)
        
        self.segment_id = segment_id
        self.on_voice_change = on_voice_change
        
        # Segment number
        self.id_label = ctk.CTkLabel(
            self,
            text=f"{segment_id + 1}.",
            width=40
        )
        self.id_label.pack(side="left", padx=5)
        
        # Text preview
        self.text_label = ctk.CTkLabel(
            self,
            text=text_preview,
            width=400,
            anchor="w"
        )
        self.text_label.pack(side="left", padx=5, fill="x", expand=True)
        
        # Voice selector
        self.voice_combo = ctk.CTkComboBox(
            self,
            values=voices,
            command=self._on_voice_selected,
            width=150
        )
        self.voice_combo.pack(side="right", padx=5)
        
        if voices:
            self.voice_combo.set(voices[0])
    
    def _on_voice_selected(self, voice: str) -> None:
        """Handle voice selection.
        
        Args:
            voice: Selected voice name
        """
        if self.on_voice_change:
            self.on_voice_change(self.segment_id, voice)
    
    def get_selected_voice(self) -> str:
        """Get currently selected voice.
        
        Returns:
            Selected voice name
        """
        return self.voice_combo.get()
    
    def set_voice(self, voice: str) -> None:
        """Set selected voice.
        
        Args:
            voice: Voice name to select
        """
        self.voice_combo.set(voice)
