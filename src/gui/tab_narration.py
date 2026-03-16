"""Narration tab interface."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.workspace_manager import WorkspaceManager

from core.transcript_parser import TranscriptParser
from core.audio_utils import save_audio, merge_audio_segments
from utils.error_handler import logger, show_error_dialog
from utils.threading_helpers import CancellableWorker, run_in_thread
from utils.theme import get_theme_colors
from gui.components import AudioPlayerWidget, SegmentListRow, ColoredPreviewWindow
from gui.voice_browser import VoiceBrowserWidget
from gui.speaker_assignment import SpeakerAssignmentPanel


class NarrationTab(ctk.CTkFrame):
    """Multi-voice narration tab."""
    
    def __init__(self, parent, tts_engine, voice_library, config, workspace_mgr: 'WorkspaceManager'):
        super().__init__(parent)
        
        self.tts_engine = tts_engine
        self.voice_library = voice_library
        self.config = config
        self.workspace_mgr = workspace_mgr
        self.parser = TranscriptParser()
        self._base_model_loading = False
        
        self.transcript_text = ""
        self.segments = []
        self.voice_mapping = {}
        self.generated_segments = []  # list of (audio_array, sr) per segment
        self.last_output_path = None  # Path to the last saved narration file
        self.last_sr = None
        self.segment_regen_players = {}  # seg_idx -> AudioPlayer
        self.worker = None
        
        # Selected voice for single mode
        self.selected_voice_data = None
        
        # Speaker assignment panel for annotated mode
        self.speaker_assignment_panel = None
        
        # Segment rows for manual mode
        self.segment_rows = {}
        
        # Colored preview button reference
        self.colored_preview_button = None
        
        self._create_ui()
        
        # Pack the frame into parent
        self.pack(fill="both", expand=True)

        # Restore previous session after the UI is fully rendered
        self.after(200, self._restore_session)
    
    def _create_mode_selector(self) -> None:
        """Create voice assignment mode selector at top."""
        mode_panel = ctk.CTkFrame(self, height=120)
        mode_panel.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=(5, 0))
        mode_panel.grid_propagate(False)
        
        # Title
        title = ctk.CTkLabel(
            mode_panel,
            text="Voice Assignment Mode",
            font=("Arial", 14, "bold")
        )
        title.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Container for radio buttons and explainers
        content_frame = ctk.CTkFrame(mode_panel, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.mode_var = ctk.StringVar(value="single")
        
        # Mode options with explainers
        modes = [
            ("single", "Single Voice", "Use one voice for the entire narration"),
            ("manual", "Segment Assignment", "Assign voices to text blocks separated by blank lines"),
            ("annotated", "Annotated Speakers", "Auto-detect speakers from [Name]: dialogue format")
        ]
        
        for idx, (mode_value, mode_label, explainer) in enumerate(modes):
            # Radio button
            radio = ctk.CTkRadioButton(
                content_frame,
                text=mode_label,
                variable=self.mode_var,
                value=mode_value,
                command=lambda: self._on_mode_change(self.mode_var.get()),
                font=("Arial", 12, "bold")
            )
            radio.grid(row=idx, column=0, sticky="w", padx=5, pady=2)
            
            # Explainer text
            colors = get_theme_colors()
            explainer_label = ctk.CTkLabel(
                content_frame,
                text=explainer,
                font=("Arial", 11),
                text_color=colors["text_secondary"],
                anchor="w"
            )
            explainer_label.grid(row=idx, column=1, sticky="w", padx=(10, 5), pady=2)
    
    def _create_ui(self) -> None:
        """Create tab UI."""
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)  # Mode selector row
        self.rowconfigure(1, weight=1)  # Main content row
        
        # Mode selector at top
        self._create_mode_selector()
        
        # Left panel: Input and generation
        self._create_input_panel()
        
        # Right panel: Voice assignment
        self._create_assignment_panel()
    
    def _create_input_panel(self) -> None:
        """Create transcript input panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Transcript Narration", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Button container for Load and Parse buttons
        button_container = ctk.CTkFrame(panel, fg_color="transparent")
        button_container.pack(pady=5)
        
        # Load transcript button
        load_btn = ctk.CTkButton(
            button_container,
            text="Load Transcript File (.txt)",
            command=self._load_transcript,
            width=200
        )
        load_btn.pack(side="left", padx=5)
        
        # Parse text area button
        parse_btn = ctk.CTkButton(
            button_container,
            text="Parse And Check Text For Segments Or Speakers",
            command=self._parse_text_area,
            width=300
        )
        parse_btn.pack(side="left", padx=5)
        
        # Show Colored Preview button
        self.colored_preview_button = ctk.CTkButton(
            button_container,
            text="Show Colored Preview",
            command=self._show_colored_preview,
            width=180,
            state="disabled"
        )
        self.colored_preview_button.pack(side="left", padx=5)

        # Clear All button
        clear_btn = ctk.CTkButton(
            button_container,
            text="Clear All",
            command=self._clear_all,
            width=100,
            fg_color="#c0392b",
            hover_color="#922b21"
        )
        clear_btn.pack(side="left", padx=5)
        
        # Transcript text
        self.transcript_textbox = ctk.CTkTextbox(panel, height=200)
        self.transcript_textbox.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Statistics
        colors = get_theme_colors()
        self.stats_label = ctk.CTkLabel(panel, text="", text_color=colors["text_secondary"])
        self.stats_label.pack()
        
        # Generate button
        self.generate_button = ctk.CTkButton(
            panel,
            text="Generate Narration",
            command=self._generate_narration,
            height=40,
            font=("Arial", 14, "bold"),
            fg_color="green",
            state="disabled"
        )
        self.generate_button.pack(pady=10)
        
        # Progress
        self.progress_bar = ctk.CTkProgressBar(panel)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(panel, text="")
        self.progress_label.pack()
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            panel,
            text="Cancel",
            command=self._cancel_generation,
            state="disabled"
        )
        self.cancel_button.pack(pady=5)
        
        # Output info
        colors = get_theme_colors()
        self.output_label = ctk.CTkLabel(panel, text="", text_color=colors["success_text"])
        self.output_label.pack(pady=10)

        # Segment results panel  — shown after generation, hidden until then
        self.segment_results_outer = ctk.CTkFrame(panel)
        seg_header_row = ctk.CTkFrame(self.segment_results_outer, fg_color="transparent")
        seg_header_row.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            seg_header_row,
            text="Segment Results",
            font=("Arial", 13, "bold")
        ).pack(side="left")
        colors2 = get_theme_colors()
        ctk.CTkLabel(
            seg_header_row,
            text="Click \u21ba Re-gen to re-synthesise a single segment without regenerating everything",
            font=("Arial", 10),
            text_color=colors2["text_secondary"]
        ).pack(side="left", padx=10)
        self.segment_results_scroll = ctk.CTkScrollableFrame(self.segment_results_outer, height=180)
        self.segment_results_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 6))
        # NOT packed into panel yet — _populate_segment_results will pack it
    
    def _create_assignment_panel(self) -> None:
        """Create voice assignment panel."""
        self.assignment_panel = ctk.CTkFrame(self)
        self.assignment_panel.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(self.assignment_panel, text="Voice Assignment", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Container for dynamic content - split into left (assignment) and right (explanation)
        self.assignment_content_frame = ctk.CTkFrame(self.assignment_panel)
        self.assignment_content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Configure 2-column grid layout (75% assignment, 25% explainer)
        self.assignment_content_frame.columnconfigure(0, weight=3)  # Left: assignments (75%)
        self.assignment_content_frame.columnconfigure(1, weight=1)  # Right: explanations (25%)
        self.assignment_content_frame.rowconfigure(0, weight=1)
        
        # Left frame for assignment UI
        self.assignment_left_frame = ctk.CTkFrame(self.assignment_content_frame)
        self.assignment_left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        
        # Right frame for mode explanations
        self.assignment_right_frame = ctk.CTkFrame(self.assignment_content_frame)
        self.assignment_right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        
        # Segments list (for manual and single mode)
        self.segments_frame = ctk.CTkScrollableFrame(self.assignment_left_frame)
        self.segments_frame.pack(fill="both", expand=True)
        
        # Mode explanation label in right frame
        self.mode_explanation_label = ctk.CTkLabel(
            self.assignment_right_frame,
            text="",
            wraplength=250,
            justify="left",
            anchor="nw",
            font=("Arial", 11)
        )
        self.mode_explanation_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Parse Status label (larger, bold font)
        colors = get_theme_colors()
        self.assignment_info_label = ctk.CTkLabel(
            self.assignment_panel,
            text="Select a voice assignment mode to begin",
            text_color=colors["text_secondary"],
            font=("Arial", 14, "bold")
        )
        self.assignment_info_label.pack(pady=10)
        
        # Initialize with single voice mode UI
        self._update_mode_ui("single")
    
    def _get_color_palette(self):
        """Get the shared color palette for segments and speakers.
        
        Returns:
            list: Array of 8 distinct colors
        """
        return [
            "#3b82f6",  # blue
            "#ec4899",  # pink
            "#10b981",  # green
            "#f59e0b",  # amber
            "#8b5cf6",  # violet
            "#ef4444",  # red
            "#14b8a6",  # teal
            "#f97316",  # orange
        ]
    
    def _show_colored_preview(self) -> None:
        """Open window showing colored transcript preview."""
        if len(self.segments) == 0:
            return
        
        # Open colored preview window
        ColoredPreviewWindow(
            self,
            segments=self.segments,
            parser=self.parser,
            colors=self._get_color_palette(),
            mode=self.mode_var.get(),
            speaker_assignment_panel=self.speaker_assignment_panel
        )
    
    def _load_transcript(self) -> None:
        """Load transcript from file."""
        filepath = filedialog.askopenfilename(
            title="Load Transcript",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filepath:
            logger.info(f"Loading transcript from file: {filepath}")
            try:
                text = self.parser.load_transcript_file(filepath)
                self.transcript_textbox.delete("1.0", "end")
                self.transcript_textbox.insert("1.0", text)
                self.transcript_text = text
                
                # Update statistics
                stats = self.parser.get_statistics(text)
                stats_text = f"{stats['words']} words, {stats['sentences']} sentences"
                self.stats_label.configure(text=stats_text)
                logger.info(f"Transcript loaded successfully: {stats_text}")
                
                # Auto-parse the loaded transcript
                logger.debug("Auto-parsing loaded transcript...")
                self._parse_transcript(show_messages=False)
                
            except Exception as e:
                show_error_dialog(e, "loading transcript", self)
    
    def _parse_text_area(self) -> None:
        """Parse the current text in the text area."""
        logger.info("Parsing text area...")
        try:
            # Get text from textbox
            text = self.transcript_textbox.get("1.0", "end-1c").strip()
            
            if not text:
                logger.warning("Parse attempted with empty text area")
                messagebox.showwarning("Empty Text", "Please enter or load text to parse.")
                return
            
            self.transcript_text = text
            
            # Update statistics
            stats = self.parser.get_statistics(text)
            stats_text = f"{stats['words']} words, {stats['sentences']} sentences"
            self.stats_label.configure(text=stats_text)
            logger.info(f"Text area statistics: {stats_text}")
            
            # Parse the transcript without popup confirmation
            self._parse_transcript(show_messages=False)
            
        except Exception as e:
            show_error_dialog(e, "parsing text area", self)
    
    def _on_mode_change(self, mode: str) -> None:
        """Handle mode change."""
        logger.debug(f"Narration mode changed to: {mode}")
        
        # Always update UI for the new mode
        self._update_mode_ui(mode)
    
    def _browse_single_voice(self) -> None:
        """Open voice browser for single voice mode."""
        logger.debug("Opening voice browser for single voice mode")
        browser = VoiceBrowserWidget(
            self,
            voice_library=self.voice_library,
            tts_engine=self.tts_engine,
            config=self.config,
            on_select=self._on_single_voice_selected
        )
        browser.wait_window()
    
    def _on_single_voice_selected(self, voice_data: dict) -> None:
        """Handle voice selection for single voice mode."""
        self.selected_voice_data = voice_data
        voice_name = voice_data['name']
        voice_type = voice_data.get('type', 'cloned')
        
        logger.info(f"Selected voice for single voice mode: {voice_name} ({voice_type})")
        
        # Trigger re-parse to update UI
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        if text:
            self._parse_transcript(show_messages=False)
        self._save_session()
    
    def refresh_voice_list(self) -> None:
        """Public method to refresh voice list (called from other tabs)."""
        # Voice browser uses voice_library directly, so no refresh needed
        # But we should reset selection if the selected voice was deleted
        if self.selected_voice_data:
            voice_name = self.selected_voice_data['name']
            voice_type = self.selected_voice_data.get('type', 'cloned')
            
            # Check if voice still exists in library
            lib_voices = self.voice_library.get_all_voices()
            if not any(v['name'] == voice_name for v in lib_voices):
                logger.warning(f"Previously selected voice '{voice_name}' no longer exists")
                self.selected_voice_data = None
                # Re-parse to update UI if there's text
                text = self.transcript_textbox.get("1.0", "end-1c").strip()
                if text:
                    self._parse_transcript(show_messages=False)
    
    def _update_voice_list(self) -> None:
        """Update available voices list (deprecated - using browser now)."""
        # This method is deprecated but kept for backward compatibility
        # The voice browser now handles all voice selection
        pass
    
    def _parse_transcript(self, show_messages: bool = True) -> None:
        """Parse transcript into segments.
        
        Args:
            show_messages: Whether to show success/error messageboxes
        """
        logger.info("Starting transcript parsing...")
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        if not text:
            logger.warning("Parse attempted with empty transcript")
            if show_messages:
                messagebox.showerror("Error", "Please load or enter a transcript first.")
            return
        
        self.transcript_text = text
        mode = self.mode_var.get()
        logger.info(f"Parsing in {mode} mode, text length: {len(text)} characters")
        
        try:
            # Parse based on mode
            if mode == "single":
                # Always show the single voice UI first
                self._show_single_voice_assignment()
                
                # Require user to select a voice first
                if not self.selected_voice_data:
                    if show_messages:
                        messagebox.showwarning(
                            "No Voice Selected",
                            "Please select a voice first.\n\n"
                            "Click 'Select Voice' in the Voice Assignment panel to choose a voice."
                        )
                    logger.warning("No voice selected in single voice mode")
                    return
                
                default_voice = self.selected_voice_data['name']
                
                logger.debug(f"Using single voice: {default_voice}")
                self.segments = self.parser.parse_transcript(text, mode="single", default_voice=default_voice)
            
            elif mode == "manual":
                logger.debug("Parsing for segment voice assignment")
                self.segments = self.parser.parse_transcript(text, mode="manual")
                self._show_manual_assignment()
            
            elif mode == "annotated":
                logger.debug("Parsing annotated transcript")
                self.segments = self.parser.parse_transcript(text, mode="annotated")
                detected_speakers = self.parser.detect_speakers(text)
                
                if not detected_speakers:
                    logger.warning("No speakers detected in annotated transcript")
                    if show_messages:
                        messagebox.showwarning(
                            "No Speakers Detected",
                            "No speaker annotations found in the transcript.\n"
                            "Use format: [SpeakerName]: dialogue"
                        )
                    self._show_annotated_assignment_empty()
                    return
                
                # Count segments per speaker
                segment_counts = {}
                for segment in self.segments:
                    speaker = segment.voice  # In annotated mode, voice field contains speaker name
                    segment_counts[speaker] = segment_counts.get(speaker, 0) + 1
                
                logger.debug(f"Detected {len(detected_speakers)} speakers: {', '.join(detected_speakers)}")
                self._show_annotated_assignment(detected_speakers, segment_counts)
            
            logger.info(f"Successfully parsed {len(self.segments)} segments")
            # Generate button will be enabled/disabled by _update_parse_status based on assignments
            self._update_parse_status()
            self._save_session()
            if show_messages:
                messagebox.showinfo("Success", f"Parsed {len(self.segments)} segments")
            
        except Exception as e:
            if show_messages:
                show_error_dialog(e, "parsing transcript", self)
            else:
                logger.error(f"Error parsing transcript: {e}")
    
    def _show_manual_assignment(self) -> None:
        """Show segment voice assignment UI."""
        # Hide speaker assignment panel and show segments frame
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.pack_forget()
        
        # Ensure segments frame is visible
        self.segments_frame.pack(fill="both", expand=True)
        
        # Clear segments frame and segment rows storage
        for widget in self.segments_frame.winfo_children():
            widget.destroy()
        self.segment_rows = {}
        
        # Handle empty segments
        if len(self.segments) == 0:
            colors = get_theme_colors()
            empty_label = ctk.CTkLabel(
                self.segments_frame,
                text="Load a transcript to assign voices to segments",
                text_color=colors["text_secondary"],
                font=("Arial", 12)
            )
            empty_label.pack(pady=40)
            self._update_parse_status()
            return
        
        # Get shared color palette for segments
        segment_colors = self._get_color_palette()
        
        # Show first 50 segments (performance)
        max_show = min(50, len(self.segments))
        total_segments = len(self.segments)
        for i, segment in enumerate(self.segments[:max_show]):
            preview = self.parser.preview_segment(segment, max_length=80)
            segment_color = segment_colors[i % len(segment_colors)]
            row = SegmentListRow(
                self.segments_frame,
                segment.segment_id,
                preview,
                total_segments,
                segment_color,
                on_voice_select=self._browse_voice_for_segment
            )
            row.pack(fill="x", pady=5, padx=5)
            self.segment_rows[segment.segment_id] = row
        
        if len(self.segments) > max_show:
            colors = get_theme_colors()
            more_label = ctk.CTkLabel(
                self.segments_frame,
                text=f"... and {len(self.segments) - max_show} more segments",
                text_color=colors["text_secondary"]
            )
            more_label.pack(pady=10)
        
        self._update_parse_status()
    
    def _show_single_voice_assignment(self) -> None:
        """Show single voice assignment UI."""
        # Hide other panels
        self.segments_frame.pack_forget()
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.pack_forget()
        
        # Clear segments frame
        for widget in self.segments_frame.winfo_children():
            widget.destroy()
        
        # Re-pack segments frame for single voice UI
        self.segments_frame.pack(fill="both", expand=True)
        
        # Create single row for voice assignment
        row_frame = ctk.CTkFrame(self.segments_frame)
        row_frame.pack(fill="x", pady=10, padx=5)
        row_frame.columnconfigure(0, weight=0)
        row_frame.columnconfigure(1, weight=1)
        row_frame.columnconfigure(2, weight=0)
        
        # Voice indicator/color badge
        color_badge = ctk.CTkFrame(row_frame, width=5, height=30, fg_color="#3b82f6")
        color_badge.grid(row=0, column=0, sticky="w", padx=(5, 2))
        color_badge.grid_propagate(False)
        
        # Label
        label = ctk.CTkLabel(
            row_frame,
            text="Single Voice",
            font=("Arial", 13, "bold"),
            anchor="w"
        )
        label.grid(row=0, column=0, sticky="w", padx=(15, 5))
        
        # Current voice display
        if self.selected_voice_data:
            voice_name = self.selected_voice_data['name']
            voice_type = self.selected_voice_data.get('type', 'cloned')
            display_text = f"{voice_name} ({voice_type})"
            colors = get_theme_colors()
            text_color = colors["text_primary"]
        else:
            display_text = "No voice selected"
            colors = get_theme_colors()
            text_color = colors["text_secondary"]
        
        voice_display = ctk.CTkLabel(
            row_frame,
            text=display_text,
            anchor="w",
            text_color=text_color
        )
        voice_display.grid(row=0, column=1, sticky="w", padx=10)
        
        # Select button
        select_btn = ctk.CTkButton(
            row_frame,
            text="Select Voice",
            width=120,
            command=self._browse_single_voice
        )
        select_btn.grid(row=0, column=2, sticky="e", padx=5)
        
        # Update Parse Status
        self._update_parse_status()
    
    def _update_mode_ui(self, mode: str) -> None:
        """Update voice assignment UI for current mode (with or without parsed text).
        
        This method orchestrates UI updates when mode changes, regardless of whether
        transcript text exists. It either parses and populates data, or shows empty state.
        """
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        
        if text:
            # Parse and populate with data
            logger.debug(f"Parsing transcript for mode: {mode}")
            self._parse_transcript(show_messages=False)
        else:
            # Show empty state for this mode
            logger.debug(f"Showing empty state for mode: {mode}")
            if mode == "single":
                self._show_single_voice_assignment()
            elif mode == "manual":
                self._show_manual_assignment()
            elif mode == "annotated":
                self._show_annotated_assignment_empty()
        
        # Update mode explanation text
        self._update_mode_explanation(mode)
    
    def _update_mode_explanation(self, mode: str) -> None:
        """Update the explanation text in the right panel based on current mode."""
        explanations = {
            "single": (
                "Single Voice Mode\n\n"
                "How it works:\n"
                "• Uses one voice for the entire narration\n"
                "• No speaker detection or parsing\n"
                "• The transcript is narrated as-is\n\n"
                "Voice Assignment:\n"
                "• Select your preferred voice above\n"
                "• The same voice will be used for all text\n\n"
                "Best for:\n"
                "• Audiobooks\n"
                "• Simple narrations\n"
                "• Consistent voice throughout"
            ),
            "manual": (
                "Segment Assignment Mode\n\n"
                "What is a Segment?\n"
                "A segment = a block of text separated by blank lines.\n"
                "Text is auto-split wherever there's a blank line.\n\n"
                "Segment Detection Rules:\n"
                "• Splits at: blank lines (empty line between text)\n"
                "• Multiple sentences in one block = one segment\n"
                "• Line breaks within a block are preserved\n"
                "• Each text block = one assignable segment\n\n"
                "Examples:\n\n"
                "Input with blank line:\n"
                "Hello my name is Sam.\n"
                "\n"
                "Hello my name is Susan.\n"
                "→ Segment 1: \"Hello my name is Sam.\"\n"
                "→ Segment 2: \"Hello my name is Susan.\"\n\n"
                "Input without blank line:\n"
                "Hello my name is Sam.\n"
                "Hello my name is Susan.\n"
                "→ Segment 1: \"Hello my name is Sam.\n"
                "Hello my name is Susan.\"\n\n"
                "Voice Assignment:\n"
                "• Select a voice for each segment individually\n"
                "• Different segments can use different voices\n\n"
                "Best for:\n"
                "• Paragraph-level voice control\n"
                "• Narrations with distinct sections\n"
                "• Organizing longer texts by topic/speaker"
            ),
            "annotated": (
                "Annotated Speaker Mode\n\n"
                "How it works:\n"
                "• Automatically detects speakers from text\n"
                "• Uses [SpeakerName]: dialogue format\n"
                "• Groups all lines by speaker\n\n"
                "Format Example:\n"
                "[Alice]: Hello there!\n"
                "[Bob]: Hi Alice, how are you?\n"
                "[Alice]: I'm doing great!\n\n"
                "Voice Assignment:\n"
                "• Assign one voice per detected speaker\n"
                "• All lines by that speaker use same voice\n\n"
                "Best for:\n"
                "• Dialogue scripts\n"
                "• Plays and screenplays\n"
                "• Multi-character conversations"
            )
        }
        
        explanation_text = explanations.get(mode, "")
        self.mode_explanation_label.configure(text=explanation_text)
    
    def _show_annotated_assignment_empty(self) -> None:
        """Show empty state for annotated mode (no speakers detected or no text)."""
        # Hide other panels
        self.segments_frame.pack_forget()
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.destroy()
            self.speaker_assignment_panel = None
        
        # Clear segments frame and show empty message
        for widget in self.segments_frame.winfo_children():
            widget.destroy()
        
        self.segments_frame.pack(fill="both", expand=True)
        
        colors = get_theme_colors()
        empty_label = ctk.CTkLabel(
            self.segments_frame,
            text="Load a transcript with [Speaker]: format\nto detect and assign speakers",
            text_color=colors["text_secondary"],
            font=("Arial", 12),
            justify="center"
        )
        empty_label.pack(pady=40)
        
        self._update_parse_status()
    
    def _show_annotated_assignment(self, speakers: list, segment_counts: dict) -> None:
        """Show annotated mode speaker assignment UI."""
        # Hide segments frame and show speaker assignment panel
        self.segments_frame.pack_forget()
        
        # Destroy old speaker assignment panel if exists
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.destroy()
        
        # Create new speaker assignment panel
        self.speaker_assignment_panel = SpeakerAssignmentPanel(
            self.assignment_left_frame,
            voice_library=self.voice_library,
            tts_engine=self.tts_engine,
            config=self.config,
            speakers=speakers,
            segment_counts=segment_counts,
            on_assignment_change=self._on_speaker_assignment_change
        )
        self.speaker_assignment_panel.pack(fill="both", expand=True)
        
        self._update_parse_status()
        
        logger.info(f"Created speaker assignment panel with {len(speakers)} speakers")
    
    def _browse_voice_for_segment(self, segment_id: int) -> None:
        """Open voice browser for a specific segment.
        
        Args:
            segment_id: ID of segment to assign voice to
        """
        logger.debug(f"Opening voice browser for segment: {segment_id}")
        
        def on_voice_select(voice_data: dict) -> None:
            self._on_segment_voice_assigned(segment_id, voice_data)
        
        browser = VoiceBrowserWidget(
            self,
            voice_library=self.voice_library,
            tts_engine=self.tts_engine,
            config=self.config,
            on_select=on_voice_select
        )
        browser.wait_window()
    
    def _on_segment_voice_assigned(self, segment_id: int, voice_data: dict) -> None:
        """Handle voice assignment to a segment.
        
        Args:
            segment_id: ID of segment
            voice_data: Selected voice data dictionary
        """
        # Store the voice data in mapping
        self.voice_mapping[segment_id] = voice_data
        
        # Update the UI if row exists
        if segment_id in self.segment_rows:
            self.segment_rows[segment_id].set_voice(voice_data)
        
        logger.info(f"Assigned voice '{voice_data['name']}' to segment {segment_id}")
        self._update_parse_status()
        self._save_session()
    
    def _on_speaker_assignment_change(self, speaker: str, voice_data: dict) -> None:
        """Handle speaker-to-voice assignment changes."""
        logger.debug(f"Speaker '{speaker}' assigned to voice '{voice_data['name']}'")
        # The assignment is stored in the speaker_assignment_panel
        # We'll use it during generation
        self._update_parse_status()
        self._save_session()
    
    def _update_parse_status(self) -> None:
        """Update the Parse Status label based on current transcript and assignment state."""
        # Check if transcript is empty or whitespace
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        colors = get_theme_colors()
        
        if not text:
            # Empty transcript
            self.assignment_info_label.configure(
                text="Transcript Is Empty",
                text_color=colors["text_secondary"]
            )
            self.generate_button.configure(state="disabled")
            # Disable colored preview button
            if self.colored_preview_button:
                self.colored_preview_button.configure(state="disabled")
            return
        
        # Transcript has content - check mode
        mode = self.mode_var.get()
        
        # Update colored preview button state based on mode
        if self.colored_preview_button:
            if mode in ["manual", "annotated"] and len(self.segments) > 0:
                # Enable preview button for segment/speaker modes with segments
                self.colored_preview_button.configure(state="normal")
            else:
                # Disable for single mode or when no segments
                self.colored_preview_button.configure(state="disabled")
        
        if mode == "single":
            # Single voice mode - check if voice is selected
            if self.selected_voice_data:
                self.assignment_info_label.configure(
                    text="Voice Model Selected",
                    text_color=colors["success_text"]
                )
                self.generate_button.configure(state="normal")
            else:
                self.assignment_info_label.configure(
                    text="No Voice Model Is Selected",
                    text_color=colors["error_text"]
                )
                self.generate_button.configure(state="disabled")
        
        elif mode == "manual":
            # Manual/segment mode - check assignment completion
            total_segments = len(self.segments)
            assigned_segments = len(self.voice_mapping)
            
            if assigned_segments < total_segments:
                # Not all assigned
                self.assignment_info_label.configure(
                    text=f"{total_segments} Segments Detected - Must Assign All Segments Voices",
                    text_color=colors["error_text"]
                )
                self.generate_button.configure(state="disabled")
            else:
                # All assigned
                self.assignment_info_label.configure(
                    text=f"{total_segments} Segments Detected - All Segments Assigned Voices",
                    text_color=colors["success_text"]
                )
                self.generate_button.configure(state="normal")
        
        elif mode == "annotated":
            # Annotated speaker mode
            if not self.speaker_assignment_panel:
                # No speaker panel = no speakers detected
                self.assignment_info_label.configure(
                    text="No Speaker Detected",
                    text_color=colors["error_text"]
                )
                self.generate_button.configure(state="disabled")
            else:
                # Have speaker panel - check completion
                speakers = self.speaker_assignment_panel.speakers
                total_speakers = len(speakers)
                
                if not self.speaker_assignment_panel.is_complete():
                    # Not all speakers assigned
                    self.assignment_info_label.configure(
                        text=f"{total_speakers} Speakers Detected - Must Assign All Speakers Voices",
                        text_color=colors["error_text"]
                    )
                    self.generate_button.configure(state="disabled")
                else:
                    # All speakers assigned
                    self.assignment_info_label.configure(
                        text=f"{total_speakers} Speakers Detected - All Speakers Assigned Voices",
                        text_color=colors["success_text"]
                    )
                    self.generate_button.configure(state="normal")
    
    def _generate_narration(self) -> None:
        """Generate narration from segments."""
        logger.info("Starting narration generation...")
        if not self.segments:
            logger.warning("Generate attempted with no segments")
            messagebox.showerror("Error", "No segments to generate. Parse transcript first.")
            return
        
        # Ensure all segments have voices assigned
        mode = self.mode_var.get()
        logger.debug(f"Generation mode: {mode}, Total segments: {len(self.segments)}")
        
        if mode == "manual":
            logger.debug("Applying voice mappings for segment assignment mode")
            # Update segments with voice mapping
            for segment in self.segments:
                if segment.segment_id in self.voice_mapping:
                    voice_data = self.voice_mapping[segment.segment_id]
                    segment.voice = voice_data['name']
                elif not segment.voice:
                    # Use selected voice as default if available
                    if self.selected_voice_data:
                        segment.voice = self.selected_voice_data['name']
                    else:
                        logger.error("No default voice available for unassigned segments")
                        messagebox.showerror("Error", "Some segments don't have voices assigned and no default voice is selected.")
                        return
        
        elif mode == "annotated":
            logger.debug("Applying speaker-to-voice assignments for annotated mode")
            # Check if all speakers have voice assignments
            if not self.speaker_assignment_panel or not self.speaker_assignment_panel.is_complete():
                logger.error("Not all speakers have voice assignments")
                messagebox.showerror(
                    "Missing Assignments",
                    "Please assign voices to all detected speakers before generating."
                )
                return
            
            # Get speaker assignments
            speaker_assignments = self.speaker_assignment_panel.get_assignments()
            
            # Map segments to voices based on speaker assignments
            for segment in self.segments:
                speaker = segment.voice  # In annotated mode, voice field contains speaker name
                if speaker in speaker_assignments:
                    voice_data = speaker_assignments[speaker]
                    segment.voice = voice_data['name']
                else:
                    logger.error(f"No voice assignment found for speaker: {speaker}")
                    messagebox.showerror(
                        "Assignment Error",
                        f"Speaker '{speaker}' does not have a voice assigned."
                    )
                    return
        
        # Validate voices
        available_voices = []
        
        lib_voices = self.voice_library.get_all_voices()
        for voice in lib_voices:
            available_voices.append(voice['name'])
        
        logger.debug(f"Validating voices against {len(available_voices)} available voices")
        is_valid, missing = self.parser.validate_segment_voices(self.segments, available_voices)
        
        if not is_valid:
            logger.error(f"Voice validation failed. Missing voices: {missing}")
            messagebox.showerror(
                "Validation Error",
                f"Some segments reference unknown voices:\n{', '.join(missing)}\n\n"
                "Check speaker annotations or voice assignments."
            )
            return
        
        logger.info("Voice validation passed, starting generation process...")
        # Disable UI
        self.generate_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        
        # Hide previous segment results while regenerating
        if self.segment_results_outer.winfo_manager():
            self.segment_results_outer.pack_forget()
        
        self.generated_segments = []
        self.last_output_path = None
        self.last_sr = None
        
        def generate_task(progress_callback):
            """Background generation task."""
            segments_audio = []
            total = len(self.segments)
            logger.info(f"Starting background generation task for {total} segments")
            
            # Get generation parameters from config
            gen_params = self.config.get("generation_params", {})
            logger.debug(f"Using generation params: {gen_params}")
            
            task_start = time.time()
            seg_elapsed_times = []
            
            def _fmt_duration(secs: float) -> str:
                """Format seconds into a human-readable duration string."""
                secs = int(secs)
                if secs < 60:
                    return f"{secs}s"
                m, s = divmod(secs, 60)
                if secs < 3600:
                    return f"{m}m {s:02d}s"
                h, m = divmod(m, 60)
                return f"{h}h {m:02d}m"
            
            for i, segment in enumerate(self.segments):
                # Check for cancellation
                if self.worker and self.worker.stop_flag.is_set():
                    logger.info("Generation cancelled by user")
                    return None
                
                # Compute ETA from average of completed segment durations
                elapsed_total = time.time() - task_start
                if seg_elapsed_times:
                    avg_seg = sum(seg_elapsed_times) / len(seg_elapsed_times)
                    eta_secs = avg_seg * (total - i)
                    eta_str = f"ETA ~{_fmt_duration(eta_secs)}"
                else:
                    eta_str = "ETA estimating..."
                
                # Update progress
                progress = int((i / total) * 100)
                progress_callback(
                    progress,
                    f"Segment {i+1} / {total}  \u2022  {eta_str}  \u2022  Elapsed: {_fmt_duration(elapsed_total)}"
                )
                logger.debug(f"Generating segment {i+1}/{total} - voice: {segment.voice}, text: '{segment.text[:50]}...'")
                
                seg_start = time.time()
                
                text = segment.text
                voice = segment.voice
                voice_data = self.voice_library.get_voice_by_name(voice)
                if voice_data:
                    voice_type = voice_data.get('type', 'cloned')
                    if voice_type == "cloned":
                        # Cloned voice - load prompt and use Base model
                        logger.debug(f"Loading cloned voice: {voice_data['id']}")
                        try:
                            # Ensure Base model is loaded
                            if self.tts_engine.base_model is None:
                                logger.info("Base model not loaded, loading now...")
                                model_size = self.config.get("active_model", "1.7B")
                                self.tts_engine.load_base_model(model_size)
                            
                            # Load voice clone prompt
                            voice_prompt = self.voice_library.load_voice_clone_prompt(voice_data["id"])
                            
                            # Generate with cloned voice
                            wavs, sr = self.tts_engine.generate_voice_clone(
                                text=text,
                                language=voice_data.get("language", "Auto"),
                                voice_clone_prompt=voice_prompt,
                                **gen_params
                            )
                            logger.debug(f"Cloned voice generation successful")
                            
                            # Track usage
                            self.voice_library.increment_usage(voice_data["id"])
                        except Exception as e:
                            logger.error(f"Failed to use cloned voice: {e}")
                            raise
                    
                    elif voice_type == "designed":
                        # Designed voice - use VoiceDesign model with description
                        logger.debug(f"Using designed voice: {voice_data['id']}")
                        try:
                            # Ensure VoiceDesign model is loaded
                            if self.tts_engine.voice_design_model is None:
                                logger.info("VoiceDesign model not loaded, loading now...")
                                model_size = self.config.get("active_model", "1.7B")
                                self.tts_engine.load_voice_design_model(model_size)
                            
                            # Generate with voice design
                            wavs, sr = self.tts_engine.generate_voice_design(
                                text=text,
                                language=voice_data.get("language", "Auto"),
                                instruct=voice_data.get("description", ""),
                                **gen_params
                            )
                            logger.debug(f"Designed voice generation successful")
                            
                            # Track usage
                            self.voice_library.increment_usage(voice_data["id"])
                        except Exception as e:
                            logger.error(f"Failed to use designed voice: {e}")
                            raise
                    else:
                        logger.error(f"Unknown voice type: {voice_type}")
                        continue
                else:
                    logger.error(f"Voice not found: {voice}")
                    continue
                
                seg_elapsed_times.append(time.time() - seg_start)
                logger.debug(f"Segment {i+1} generated successfully ({seg_elapsed_times[-1]:.1f}s)")
                segments_audio.append((wavs[0], sr))
            
            total_elapsed = time.time() - task_start
            logger.info(f"All {total} segments generated successfully in {_fmt_duration(total_elapsed)}")
            return segments_audio
        
        def on_progress(percentage, message):
            """Update progress during generation."""
            self.progress_bar.set(percentage / 100.0)
            self.progress_label.configure(text=message)
            logger.debug(f"Narration progress: {percentage:.1f}% - {message}")
        
        def on_success(result):
            """Handle successful narration generation."""
            logger.info("Processing narration success in UI thread")
            try:
                if result is None:
                    # Cancelled
                    logger.info("Narration generation was cancelled")
                    self.progress_label.configure(text="Generation cancelled")
                    self._reset_generate_ui()
                    return
                
                self.progress_bar.set(1.0)
                self.progress_label.configure(text="Merging segments...")
                logger.debug(f"Merging {len(result)} audio segments...")
                
                # Merge segments
                audio_segments = [seg[0] for seg in result]
                sr = result[0][1]
                merged = merge_audio_segments(audio_segments, sr)
                
                # Save output
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = self.workspace_mgr.get_narrations_dir() / f"narration_{timestamp}"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = output_dir / "narration_full.wav"
                logger.info(f"Saving narration to: {output_file}")
                save_audio(merged, sr, str(output_file))

                # Save companion files
                try:
                    self._save_narration_companions(output_dir, output_file, merged, sr, timestamp)
                except Exception as ce:
                    logger.warning(f"Could not save companion files: {ce}")

                # Store results for per-segment re-generation
                self.generated_segments = result
                self.last_output_path = output_file
                self.last_sr = sr
                
                self.output_label.configure(text=f"Saved: {output_file}")
                self.progress_label.configure(text="Complete!")
                
                self._reset_generate_ui()
                self._populate_segment_results()
                logger.info("Narration generation completed successfully")
                messagebox.showinfo("Success", f"Narration generated!\n\nSaved to:\n{output_file}")
            except Exception as e:
                logger.error(f"Error in success callback: {e}", exc_info=True)
                show_error_dialog(e, "processing narration result", self)
        
        def on_error(error):
            """Handle narration generation error."""
            logger.error(f"Narration generation failed: {error}")
            show_error_dialog(error, "generating narration", self)
            self._reset_generate_ui()
        
        # Start generation with proper callback capture
        logger.info("Starting narration background worker thread...")
        
        def success_wrapper(result):
            logger.info("Narration task completed, scheduling UI update")
            self.after(0, lambda: on_success(result))
        
        def error_wrapper(error):
            logger.error(f"Narration task failed: {error}")
            self.after(0, lambda: on_error(error))
        
        self.worker = CancellableWorker(
            generate_task,
            kwargs={"progress_callback": on_progress},
            success_callback=success_wrapper,
            error_callback=error_wrapper
        )
        self.worker.start()
        logger.debug("Worker thread started")

    def _save_narration_companions(self, output_dir, output_file, merged_audio, sr, timestamp: str) -> None:
        """Save narration_transcript.txt and narration_info.txt alongside the wav."""
        from pathlib import Path as _Path

        mode = self.mode_var.get()
        mode_labels = {
            "single": "Single Voice",
            "manual": "Segment Assignment",
            "annotated": "Annotated Speakers",
        }
        mode_label = mode_labels.get(mode, mode)

        gen_params = self.config.get("generation_params", {})
        active_model = self.config.get("active_model") or self.config.get("model_size", "?")
        device = self.config.get("device", "?")
        total_duration = len(merged_audio) / sr if sr else 0

        # ── transcript ────────────────────────────────────────────────
        transcript_text = self.transcript_textbox.get("1.0", "end-1c").strip()
        transcript_file = output_dir / "narration_transcript.txt"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        # ── info / readme ─────────────────────────────────────────────
        lines = []
        lines.append("=" * 60)
        lines.append("NARRATION GENERATION INFO")
        lines.append("=" * 60)
        lines.append(f"Generated : {timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} "
                     f"{timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}")
        lines.append(f"Output    : {output_file.name}")
        lines.append(f"Duration  : {total_duration:.1f}s  ({total_duration/60:.2f} min)")
        lines.append(f"Segments  : {len(self.segments)}")
        lines.append("")

        lines.append("── MODE ─────────────────────────────────────────────────")
        lines.append(f"  {mode_label}")
        lines.append("")

        lines.append("── MODEL & DEVICE ───────────────────────────────────────")
        lines.append(f"  Model  : Qwen2.5-{active_model}")
        lines.append(f"  Device : {device}")
        lines.append("")

        lines.append("── GENERATION PARAMETERS ────────────────────────────────")
        for k, v in gen_params.items():
            lines.append(f"  {k:<22}: {v}")
        lines.append("")

        lines.append("── VOICE ASSIGNMENTS ────────────────────────────────────")
        if mode == "single" and self.selected_voice_data:
            vd = self.selected_voice_data
            lines.append(f"  Voice : {vd['name']}  [{vd.get('type','?')}]  (id: {vd.get('id','?')})")
        elif mode == "manual":
            for seg in self.segments:
                vd = self.voice_library.get_voice_by_name(seg.voice) or {}
                preview = seg.text[:50].replace("\n", " ") + ("…" if len(seg.text) > 50 else "")
                lines.append(f"  Seg {seg.segment_id + 1:>3} | {seg.voice:<25} [{vd.get('type','?')}] | {preview}")
        elif mode == "annotated" and self.speaker_assignment_panel:
            for speaker, vd in self.speaker_assignment_panel.get_assignments().items():
                lines.append(f"  {speaker:<20} → {vd['name']:<25} [{vd.get('type','?')}]  (id: {vd.get('id','?')})")
        else:
            lines.append("  (no assignments recorded)")
        lines.append("")
        lines.append("=" * 60)

        info_file = output_dir / "narration_info.txt"
        with open(info_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Saved companion files: {transcript_file.name}, {info_file.name}")

    def _cancel_generation(self) -> None:
        """Cancel current generation."""
        if self.worker:
            self.worker.stop()
            self.cancel_button.configure(state="disabled")
    
    def _reset_generate_ui(self) -> None:
        """Reset generation UI."""
        # Re-check assignments to determine if generate button should be enabled
        self._update_parse_status()
        self.cancel_button.configure(state="disabled")
        self.worker = None

    def _clear_all(self) -> None:
        """Reset the narration tab to its default blank state."""
        from tkinter import messagebox as _mb
        if not _mb.askyesno("Clear All", "Clear all text, voice assignments, and results?", parent=self):
            return

        logger.info("Clearing narration tab")

        # Cancel any running generation
        if self.worker:
            self.worker.stop_flag.set()
            self.worker = None

        # Clear data state
        self.segments = []
        self.voice_mapping = {}
        self.generated_segments = []
        self.last_output_path = None
        self.last_sr = None
        self.transcript_text = ""
        self.selected_voice_data = None
        for player in self.segment_regen_players.values():
            try:
                player.stop()
            except Exception:
                pass
        self.segment_regen_players = {}

        # Clear transcript textbox
        self.transcript_textbox.delete("1.0", "end")

        # Reset stats/labels
        self.stats_label.configure(text="")
        self.progress_bar.set(0)
        self.progress_label.configure(text="")
        self.output_label.configure(text="")

        # Hide segment results panel
        if self.segment_results_outer.winfo_manager():
            self.segment_results_outer.pack_forget()
        for w in self.segment_results_scroll.winfo_children():
            w.destroy()

        # Reset buttons
        self.generate_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.colored_preview_button.configure(state="disabled")

        # Reset mode to single
        self.mode_var.set("single")
        self._on_mode_change("single")

        # Destroy speaker assignment panel
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.destroy()
            self.speaker_assignment_panel = None

        # Clear segments frame widgets and rows
        self.segment_rows = {}
        for w in self.segments_frame.winfo_children():
            w.destroy()

        # Wipe the saved session so it doesn't restore on next launch
        if self.workspace_mgr:
            try:
                session_file = self.workspace_mgr.get_narration_session_file()
                if session_file.exists():
                    session_file.unlink()
            except Exception as e:
                logger.debug(f"Could not delete narration session file: {e}")

        logger.info("Narration tab cleared")

    # ------------------------------------------------------------------
    # Per-segment regeneration
    # ------------------------------------------------------------------

    def _populate_segment_results(self) -> None:
        """Show per-segment results panel after a successful generation."""
        if not self.generated_segments or not self.segments:
            return

        # Clear any previous rows and player references
        for w in self.segment_results_scroll.winfo_children():
            w.destroy()
        # Stop and remove old players
        for player in self.segment_regen_players.values():
            try:
                player.stop()
            except Exception:
                pass
        self.segment_regen_players = {}

        colors = get_theme_colors()
        color_palette = self._get_color_palette()

        for i, (audio, sr) in enumerate(self.generated_segments):
            if i >= len(self.segments):
                break
            seg = self.segments[i]
            color = color_palette[i % len(color_palette)]

            row = ctk.CTkFrame(self.segment_results_scroll, border_width=1)
            row.pack(fill="x", padx=4, pady=3)
            row.columnconfigure(1, weight=1)

            # Colored left badge
            badge = ctk.CTkFrame(row, width=5, height=36, fg_color=color)
            badge.grid(row=0, column=0, padx=(4, 6), pady=4, sticky="ns")
            badge.grid_propagate(False)

            # Info area
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

            ctk.CTkLabel(
                info, text=f"#{i + 1}", font=("Arial", 11, "bold"),
                text_color=color, width=30, anchor="w"
            ).pack(side="left")
            ctk.CTkLabel(
                info, text=f"[{seg.voice}]", font=("Arial", 10),
                text_color=colors["text_secondary"], anchor="w"
            ).pack(side="left", padx=(0, 6))
            preview = seg.text[:45].replace("\n", " ") + ("..." if len(seg.text) > 45 else "")
            ctk.CTkLabel(
                info, text=preview, font=("Arial", 11), anchor="w"
            ).pack(side="left", fill="x", expand=True)

            # Buttons
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.grid(row=0, column=2, padx=(4, 6), pady=4)

            from core.audio_utils import AudioPlayer
            player = AudioPlayer()
            self.segment_regen_players[i] = player

            play_btn = ctk.CTkButton(
                btn_frame, text="\u25b6 Play", width=78, height=26
            )
            play_btn.configure(
                command=lambda idx=i, pb=play_btn: self._play_segment(idx, pb)
            )
            play_btn.pack(side="left", padx=2)

            regen_btn = ctk.CTkButton(
                btn_frame, text="\u21ba Re-gen", width=88, height=26
            )
            regen_btn.configure(
                command=lambda idx=i, rb=regen_btn: self._regenerate_segment(idx, rb)
            )
            regen_btn.pack(side="left", padx=2)

        # Make the panel visible
        self.segment_results_outer.pack(fill="both", expand=False, padx=10, pady=(0, 6))

    def _play_segment(self, seg_idx: int, play_btn: ctk.CTkButton) -> None:
        """Toggle playback for a specific generated segment."""
        player = self.segment_regen_players.get(seg_idx)
        if player is None:
            return

        if player.is_playing():
            player.stop()
            try:
                if play_btn.winfo_exists():
                    play_btn.configure(text="\u25b6 Play")
            except Exception:
                pass
        else:
            if not self.generated_segments or seg_idx >= len(self.generated_segments):
                return
            audio, sr = self.generated_segments[seg_idx]

            def on_done():
                try:
                    if play_btn.winfo_exists():
                        play_btn.configure(text="\u25b6 Play")
                except Exception:
                    pass

            try:
                if play_btn.winfo_exists():
                    play_btn.configure(text="\u23f9 Stop")
            except Exception:
                pass
            player.play(audio, sr, callback=on_done)

    def _regenerate_segment(self, seg_idx: int, regen_btn: ctk.CTkButton) -> None:
        """Re-generate a single segment and update the merged output file."""
        if not self.generated_segments or seg_idx >= len(self.segments):
            return

        seg = self.segments[seg_idx]
        voice_data = self.voice_library.get_voice_by_name(seg.voice)
        if not voice_data:
            messagebox.showerror("Error", f"Voice '{seg.voice}' not found in library.", parent=self)
            return

        regen_btn.configure(state="disabled", text="\u23f3 Generating...")
        gen_params = self.config.get("generation_params", {})

        def regen_task():
            voice_type = voice_data.get("type")
            if voice_type == "cloned":
                if self.tts_engine.base_model is None:
                    self.tts_engine.load_base_model(self.config.get("active_model", "1.7B"))
                voice_prompt = self.voice_library.load_voice_clone_prompt(voice_data["id"])
                wavs, sr = self.tts_engine.generate_voice_clone(
                    text=seg.text,
                    language=voice_data.get("language", "Auto"),
                    voice_clone_prompt=voice_prompt,
                    **gen_params
                )
            elif voice_type == "designed":
                if self.tts_engine.voice_design_model is None:
                    self.tts_engine.load_voice_design_model(self.config.get("active_model", "1.7B"))
                wavs, sr = self.tts_engine.generate_voice_design(
                    text=seg.text,
                    language=voice_data.get("language", "Auto"),
                    instruct=voice_data.get("description", ""),
                    **gen_params
                )
            else:
                raise ValueError(f"Unknown voice type: {voice_type}")

            self.voice_library.increment_usage(voice_data["id"])
            return wavs[0], sr

        def on_regen_success(result):
            new_audio, sr = result
            self.generated_segments[seg_idx] = (new_audio, sr)

            # Re-merge into a new incremented file, preserving previous versions
            try:
                audio_segs = [s[0] for s in self.generated_segments]
                merged = merge_audio_segments(audio_segs, sr)

                output_dir = self.last_output_path.parent
                existing = list(output_dir.glob("narration_full_v*.wav"))
                next_version = len(existing) + 2  # v2 on first regen, v3 next, etc.
                new_path = output_dir / f"narration_full_v{next_version}.wav"
                save_audio(merged, sr, str(new_path))
                self.last_output_path = new_path

                self.output_label.configure(
                    text=f"Segment {seg_idx + 1} updated \u2192 {new_path}"
                )
                logger.info(f"Segment {seg_idx + 1} re-generated successfully, saved as {new_path.name}")
            except Exception as e:
                logger.error(f"Error saving re-generated audio: {e}")

            try:
                if regen_btn.winfo_exists():
                    regen_btn.configure(state="normal", text="\u21ba Re-gen")
            except Exception:
                pass

        def on_regen_error(err):
            logger.error(f"Segment {seg_idx + 1} re-gen failed: {err}")
            show_error_dialog(err, f"re-generating segment {seg_idx + 1}", self)
            try:
                if regen_btn.winfo_exists():
                    regen_btn.configure(state="normal", text="\u21ba Re-gen")
            except Exception:
                pass

        run_in_thread(self, regen_task, on_success=on_regen_success, on_error=on_regen_error)

    # ------------------------------------------------------------------
    # Narration session save / restore
    # ------------------------------------------------------------------

    def _save_session(self) -> None:
        """Persist current transcript + voice assignments to disk."""
        if not self.workspace_mgr:
            return
        try:
            # Build voice-mapping by segment index (not segment_id) for stability
            voice_mapping_names: dict = {}
            for seg_idx, seg in enumerate(self.segments):
                if seg_idx in self.voice_mapping:
                    voice_mapping_names[str(seg_idx)] = self.voice_mapping[seg_idx]["name"]

            speaker_assignments: dict = {}
            if self.speaker_assignment_panel:
                for speaker, vd in self.speaker_assignment_panel.get_assignments().items():
                    speaker_assignments[speaker] = vd["name"]

            session = {
                "version": 1,
                "transcript": self.transcript_textbox.get("1.0", "end-1c"),
                "mode": self.mode_var.get(),
                "voice_mapping": voice_mapping_names,
                "speaker_assignments": speaker_assignments,
                "selected_voice_name": (
                    self.selected_voice_data["name"] if self.selected_voice_data else None
                ),
            }
            self.workspace_mgr.save_narration_session(session)
        except Exception as e:
            logger.debug(f"Error saving narration session: {e}")

    def _restore_session(self) -> None:
        """Reload the last saved narration session into the UI."""
        if not self.workspace_mgr:
            return
        try:
            session = self.workspace_mgr.load_narration_session()
            if not session:
                return

            transcript = session.get("transcript", "").strip()
            mode = session.get("mode", "single")

            if not transcript:
                return

            logger.info("Restoring narration session from disk...")

            # Restore transcript text
            self.transcript_textbox.delete("1.0", "end")
            self.transcript_textbox.insert("1.0", transcript)
            self.transcript_text = transcript

            # Restore mode
            self.mode_var.set(mode)

            # For single mode the voice must be set before parsing
            if mode == "single":
                voice_name = session.get("selected_voice_name")
                if voice_name:
                    vd = self.voice_library.get_voice_by_name(voice_name)
                    if vd:
                        self.selected_voice_data = vd

            # Parse to rebuild self.segments and mode-specific UI
            self._parse_transcript(show_messages=False)

            # Apply voice mappings (manual mode)
            if mode == "manual":
                for seg_idx_str, voice_name in session.get("voice_mapping", {}).items():
                    try:
                        seg_idx = int(seg_idx_str)
                        if seg_idx < len(self.segments):
                            vd = self.voice_library.get_voice_by_name(voice_name)
                            if vd:
                                self._on_segment_voice_assigned(
                                    self.segments[seg_idx].segment_id, vd
                                )
                    except (ValueError, IndexError):
                        pass

            # Apply speaker assignments (annotated mode)
            elif mode == "annotated":
                if self.speaker_assignment_panel:
                    for speaker, voice_name in session.get("speaker_assignments", {}).items():
                        vd = self.voice_library.get_voice_by_name(voice_name)
                        if vd:
                            self.speaker_assignment_panel.set_assignment(speaker, vd)

            logger.info("Narration session restored successfully")
        except Exception as e:
            logger.error(f"Error restoring narration session: {e}")
