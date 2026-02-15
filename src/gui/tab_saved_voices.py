"""Saved voices management tab interface."""

import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from core.audio_utils import AudioPlayer
from utils.error_handler import logger


class SavedVoicesTab(ctk.CTkFrame):
    """Saved voices management tab."""
    
    def __init__(self, parent, voice_library, config, workspace_dir: Optional[Path] = None):
        """Initialize saved voices tab.
        
        Args:
            parent: Parent widget
            voice_library: Voice library instance
            config: Configuration instance
            workspace_dir: Root workspace directory (None for legacy mode)
        """
        super().__init__(parent)
        
        self.voice_library = voice_library
        self.config = config
        self.workspace_dir = workspace_dir
        self.audio_player = AudioPlayer()
        
        self.selected_voice = None
        self.selected_row_frame = None  # Track selected row for highlighting
        self.filter_type = "all"  # all, cloned, designed
        self.search_query = ""
        self.search_tags = []
        
        self._create_ui()
        self._refresh_voice_list()
        
        # Pack the frame into parent
        self.pack(fill="both", expand=True)
    
    def _create_ui(self) -> None:
        """Create tab UI."""
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)
        
        # Left panel: Voice list with search
        self._create_list_panel()
        
        # Right panel: Voice details
        self._create_details_panel()
    
    def _create_list_panel(self) -> None:
        """Create voice list panel."""
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(2, weight=1)
        
        # Title
        title = ctk.CTkLabel(list_frame, text="📚 Voice Model Library", font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, pady=(10, 5), sticky="w", padx=10)
        
        # Search and filter section
        search_frame = ctk.CTkFrame(list_frame)
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        search_frame.columnconfigure(0, weight=1)
        
        # Search bar
        search_label = ctk.CTkLabel(search_frame, text="🔍 Search:")
        search_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by name...")
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search_changed())
        
        # Filter buttons
        filter_frame = ctk.CTkFrame(search_frame)
        filter_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        filter_label = ctk.CTkLabel(filter_frame, text="Filter:")
        filter_label.pack(side="left", padx=5)
        
        self.filter_all_btn = ctk.CTkButton(
            filter_frame,
            text="All",
            command=lambda: self._set_filter("all"),
            width=70,
            fg_color="green"
        )
        self.filter_all_btn.pack(side="left", padx=2)
        
        self.filter_cloned_btn = ctk.CTkButton(
            filter_frame,
            text="Cloned",
            command=lambda: self._set_filter("cloned"),
            width=70
        )
        self.filter_cloned_btn.pack(side="left", padx=2)
        
        self.filter_designed_btn = ctk.CTkButton(
            filter_frame,
            text="Designed",
            command=lambda: self._set_filter("designed"),
            width=70
        )
        self.filter_designed_btn.pack(side="left", padx=2)
        
        # Tag search
        tag_label = ctk.CTkLabel(search_frame, text="Tags:")
        tag_label.grid(row=3, column=0, sticky="w", padx=5, pady=(10, 5))
        
        self.tag_entry = ctk.CTkEntry(search_frame, placeholder_text="Enter tags (comma-separated)...")
        self.tag_entry.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        self.tag_entry.bind("<KeyRelease>", lambda e: self._on_search_changed())
        
        # Voice count
        self.count_label = ctk.CTkLabel(search_frame, text="0 voices", font=("Arial", 10))
        self.count_label.grid(row=5, column=0, sticky="w", padx=5, pady=5)
        
        # Voice list table (scrollable)
        list_scroll = ctk.CTkScrollableFrame(list_frame)
        list_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        list_scroll.columnconfigure(0, weight=3)  # Name
        list_scroll.columnconfigure(1, weight=1)  # Type
        list_scroll.columnconfigure(2, weight=1)  # Created
        list_scroll.columnconfigure(3, weight=1)  # Usage
        list_scroll.columnconfigure(4, weight=2)  # Tags
        
        self.voice_list_frame = list_scroll
        
        # Create table header
        self._create_table_header()
    
    def _create_details_panel(self) -> None:
        """Create voice details panel."""
        details_frame = ctk.CTkFrame(self)
        details_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(details_frame, text="Voice Details", font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, pady=(10, 5), sticky="w", padx=10)
        
        # Scrollable details area
        details_scroll = ctk.CTkScrollableFrame(details_frame)
        details_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        details_scroll.columnconfigure(0, weight=1)
        
        self.details_content_frame = details_scroll
        
        # Initial empty state
        self._show_empty_details()
    
    def _create_table_header(self) -> None:
        """Create the table header row."""
        header_frame = ctk.CTkFrame(self.voice_list_frame, fg_color="gray25")
        header_frame.grid(row=0, column=0, columnspan=5, sticky="ew", padx=2, pady=(2, 5))
        header_frame.columnconfigure(0, weight=3)
        header_frame.columnconfigure(1, weight=1)
        header_frame.columnconfigure(2, weight=1)
        header_frame.columnconfigure(3, weight=1)
        header_frame.columnconfigure(4, weight=2)
        
        headers = [
            ("Name", 0),
            ("Type", 1),
            ("Created", 2),
            ("Usage", 3),
            ("Tags", 4)
        ]
        
        for text, col in headers:
            label = ctk.CTkLabel(
                header_frame,
                text=text,
                font=("Arial", 11, "bold"),
                anchor="w"
            )
            label.grid(row=0, column=col, sticky="ew", padx=8, pady=5)
        
        # Store reference for later removal during refresh
        self.table_header = header_frame
    
    def _show_empty_details(self) -> None:
        """Show empty state in details panel."""
        # Clear existing widgets
        for widget in self.details_content_frame.winfo_children():
            widget.destroy()
        
        empty_label = ctk.CTkLabel(
            self.details_content_frame,
            text="Select a voice to view details",
            font=("Arial", 14),
            text_color="gray"
        )
        empty_label.pack(pady=100)
    
    def _set_filter(self, filter_type: str) -> None:
        """Set voice type filter.
        
        Args:
            filter_type: 'all', 'cloned', or 'designed'
        """
        self.filter_type = filter_type
        
        # Update button colors
        self.filter_all_btn.configure(fg_color="green" if filter_type == "all" else "gray")
        self.filter_cloned_btn.configure(fg_color="green" if filter_type == "cloned" else "gray")
        self.filter_designed_btn.configure(fg_color="green" if filter_type == "designed" else "gray")
        
        self._refresh_voice_list()
    
    def _on_search_changed(self) -> None:
        """Handle search query change."""
        self.search_query = self.search_entry.get()
        
        # Parse tags
        tag_input = self.tag_entry.get().strip()
        if tag_input:
            self.search_tags = [t.strip() for t in tag_input.split(",") if t.strip()]
        else:
            self.search_tags = []
        
        self._refresh_voice_list()
    
    def _refresh_voice_list(self) -> None:
        """Refresh the voice list display."""
        # Clear existing voice items
        for widget in self.voice_list_frame.winfo_children():
            widget.destroy()
        
        # Clear selected row reference
        self.selected_row_frame = None
        
        # Recreate table header
        self._create_table_header()
        
        # Get filtered voices
        voice_type = None if self.filter_type == "all" else self.filter_type
        
        if self.search_query or self.search_tags:
            voices = self.voice_library.search_voices(
                query=self.search_query,
                tags=self.search_tags if self.search_tags else None,
                voice_type=voice_type
            )
        else:
            voices = self.voice_library.get_all_voices(voice_type)
        
        # Sort by creation date (newest first)
        voices.sort(key=lambda v: v.get("created", ""), reverse=True)
        
        # Update count
        self.count_label.configure(text=f"{len(voices)} voice{'s' if len(voices) != 1 else ''}")
        
        # Create voice items as table rows
        for idx, voice in enumerate(voices):
            self._create_voice_row(voice, idx + 1)
        
        # Show message if no voices
        if not voices:
            no_voices_label = ctk.CTkLabel(
                self.voice_list_frame,
                text="No voices found" if self.search_query or self.search_tags else "No saved voices yet",
                text_color="gray"
            )
            no_voices_label.grid(row=1, column=0, columnspan=5, pady=20)
    
    def _create_voice_row(self, voice: dict, row_num: int) -> None:
        """Create a voice table row.
        
        Args:
            voice: Voice data dictionary
            row_num: Row number in the table
        """
        # Create clickable row frame
        row_frame = ctk.CTkFrame(
            self.voice_list_frame,
            fg_color="gray20" if row_num % 2 == 0 else "gray15",
            cursor="hand2"
        )
        row_frame.grid(row=row_num, column=0, columnspan=5, sticky="ew", padx=2, pady=1)
        row_frame.columnconfigure(0, weight=3)
        row_frame.columnconfigure(1, weight=1)
        row_frame.columnconfigure(2, weight=1)
        row_frame.columnconfigure(3, weight=1)
        row_frame.columnconfigure(4, weight=2)
        
        # Name column
        name_label = ctk.CTkLabel(
            row_frame,
            text=voice["name"],
            font=("Arial", 11),
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        
        # Type column
        type_color = "#4a90e2" if voice["type"] == "cloned" else "#e24a90"
        type_label = ctk.CTkLabel(
            row_frame,
            text=voice["type"].capitalize(),
            font=("Arial", 10),
            text_color=type_color,
            anchor="w"
        )
        type_label.grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        
        # Created column
        created_date = self._format_date_short(voice.get("created", ""))
        created_label = ctk.CTkLabel(
            row_frame,
            text=created_date,
            font=("Arial", 10),
            text_color="gray",
            anchor="w"
        )
        created_label.grid(row=0, column=2, sticky="ew", padx=8, pady=6)
        
        # Usage column
        usage_count = voice.get("usage_count", 0)
        usage_label = ctk.CTkLabel(
            row_frame,
            text=str(usage_count),
            font=("Arial", 10),
            text_color="gray",
            anchor="w"
        )
        usage_label.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
        
        # Tags column
        tags_text = ", ".join(voice.get("tags", [])[:3])  # Show first 3 tags
        if len(voice.get("tags", [])) > 3:
            tags_text += "..."
        tags_label = ctk.CTkLabel(
            row_frame,
            text=tags_text if tags_text else "-",
            font=("Arial", 10),
            text_color="gray",
            anchor="w"
        )
        tags_label.grid(row=0, column=4, sticky="ew", padx=8, pady=6)
        
        # Click handler
        def select_voice(e=None):
            # Unhighlight previous selection
            if self.selected_row_frame:
                # Restore original color based on row number
                orig_color = "gray20" if row_num % 2 == 0 else "gray15"
                self.selected_row_frame.configure(fg_color=orig_color)
            
            # Highlight this row
            row_frame.configure(fg_color="gray30")
            self.selected_row_frame = row_frame
            
            # Show voice details
            self._select_voice(voice)
        
        # Bind click events
        row_frame.bind("<Button-1>", select_voice)
        for widget in [name_label, type_label, created_label, usage_label, tags_label]:
            widget.bind("<Button-1>", select_voice)
    
    def _format_date_short(self, iso_date: str) -> str:
        """Format ISO date string to short format.
        
        Args:
            iso_date: ISO format date string
            
        Returns:
            Short formatted date string
        """
        try:
            dt = datetime.fromisoformat(iso_date)
            return dt.strftime("%Y-%m-%d")
        except:
            return "Unknown"
    
    def _select_voice(self, voice: dict) -> None:
        """Select and show voice details.
        
        Args:
            voice: Voice data dictionary
        """
        self.selected_voice = voice
        self._show_voice_details(voice)
        
        # Track usage
        self.voice_library.increment_usage(voice["id"])
    
    def _show_voice_details(self, voice: dict) -> None:
        """Show detailed information for selected voice.
        
        Args:
            voice: Voice data dictionary
        """
        # Stop any playing audio from previous voice before clearing widgets
        try:
            self.audio_player.stop()
        except Exception:
            pass  # Ignore if already stopped
        
        # Clear existing widgets
        for widget in self.details_content_frame.winfo_children():
            widget.destroy()
        
        # Voice name
        name_label = ctk.CTkLabel(
            self.details_content_frame,
            text=voice["name"],
            font=("Arial", 20, "bold")
        )
        name_label.pack(pady=(10, 5), anchor="w")
        
        # Type and ID
        type_color = "#4a90e2" if voice["type"] == "cloned" else "#e24a90"
        type_label = ctk.CTkLabel(
            self.details_content_frame,
            text=f"{voice['type'].upper()} VOICE  •  ID: {voice['id']}",
            font=("Arial", 11),
            text_color=type_color
        )
        type_label.pack(pady=5, anchor="w")
        
        # Separator
        separator = ctk.CTkFrame(self.details_content_frame, height=2)
        separator.pack(fill="x", pady=10)
        
        # Metadata section
        metadata_frame = ctk.CTkFrame(self.details_content_frame)
        metadata_frame.pack(fill="x", pady=10)
        
        self._add_metadata_row(metadata_frame, "Created:", self._format_date(voice.get("created", "")))
        self._add_metadata_row(metadata_frame, "Language:", voice.get("language", "Auto"))
        self._add_metadata_row(metadata_frame, "Times Used:", str(voice.get("usage_count", 0)))
        
        if voice.get("last_used"):
            self._add_metadata_row(metadata_frame, "Last Used:", self._format_date(voice["last_used"]))
        
        # Tags
        if voice.get("tags"):
            tags_frame = ctk.CTkFrame(self.details_content_frame)
            tags_frame.pack(fill="x", pady=10)
            
            tags_title = ctk.CTkLabel(tags_frame, text="Tags:", font=("Arial", 12, "bold"))
            tags_title.pack(anchor="w", pady=5)
            
            tags_text = ", ".join(f"#{tag}" for tag in voice["tags"])
            tags_label = ctk.CTkLabel(tags_frame, text=tags_text, anchor="w")
            tags_label.pack(anchor="w", padx=10)
        
        # Type-specific details
        if voice["type"] == "cloned":
            # Reference text
            ref_frame = ctk.CTkFrame(self.details_content_frame)
            ref_frame.pack(fill="x", pady=10)
            
            ref_title = ctk.CTkLabel(ref_frame, text="Reference Text:", font=("Arial", 12, "bold"))
            ref_title.pack(anchor="w", pady=5)
            
            ref_text = ctk.CTkTextbox(ref_frame, height=80, wrap="word")
            ref_text.pack(fill="x", padx=10, pady=5)
            ref_text.insert("1.0", voice.get("ref_text", ""))
            ref_text.configure(state="disabled")
            
            # Reference audio
            ref_audio_path = voice.get("ref_audio", "")
            if ref_audio_path and Path(ref_audio_path).exists():
                ref_audio_frame = ctk.CTkFrame(self.details_content_frame)
                ref_audio_frame.pack(fill="x", pady=10)
                
                ref_audio_title = ctk.CTkLabel(ref_audio_frame, text="Reference Audio:", font=("Arial", 12, "bold"))
                ref_audio_title.pack(anchor="w", pady=5)
                
                # Play button
                play_ref_btn = ctk.CTkButton(
                    ref_audio_frame,
                    text="▶ Play Reference Audio",
                    command=lambda: self._play_reference_audio(ref_audio_path),
                    width=180
                )
                play_ref_btn.pack(padx=10, pady=5, anchor="w")
            
        elif voice["type"] == "designed":
            # Description
            desc_frame = ctk.CTkFrame(self.details_content_frame)
            desc_frame.pack(fill="x", pady=10)
            
            desc_title = ctk.CTkLabel(desc_frame, text="Design Description:", font=("Arial", 12, "bold"))
            desc_title.pack(anchor="w", pady=5)
            
            desc_text = ctk.CTkTextbox(desc_frame, height=80, wrap="word")
            desc_text.pack(fill="x", padx=10, pady=5)
            desc_text.insert("1.0", voice.get("description", ""))
            desc_text.configure(state="disabled")
        
        # Test Audio Section (unified templates + custom tests)
        template_tests = voice.get("template_tests", [])
        custom_tests = voice.get("custom_tests", [])
        
        # Only show section if there are any tests
        if template_tests or custom_tests:
            test_audio_frame = ctk.CTkFrame(self.details_content_frame)
            test_audio_frame.pack(fill="both", expand=True, pady=10)
            test_audio_frame.columnconfigure(0, weight=1)
            
            # Title
            test_audio_title = ctk.CTkLabel(test_audio_frame, text="Test Audio:", font=("Arial", 12, "bold"))
            test_audio_title.pack(anchor="w", pady=(5, 5), padx=10)
            
            # Scrollable list for all test audio
            test_audio_scroll = ctk.CTkScrollableFrame(test_audio_frame, height=200)
            test_audio_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            test_audio_scroll.columnconfigure(0, weight=1)
            
            # Get template texts from config
            template_texts = self.config.get("template_test_transcripts", [
                "I am a voice model. I was created using the magic of computing.",
                "I am a voice model. A. B. C. D. E. 1. 2. 3. 4. 5",
                "I am a voice model. Row, row, row your boat, gently down the stream. Merrily, merrily, merrily, life is but a dream."
            ])
            
            row = 0
            
            # Add template tests first
            for idx, test_path in enumerate(template_tests):
                if Path(test_path).exists():
                    template_text = template_texts[idx] if idx < len(template_texts) else f"Template Test {idx+1}"
                    preview_text = template_text[:50] + "..." if len(template_text) > 50 else template_text
                    
                    test_frame = ctk.CTkFrame(test_audio_scroll)
                    test_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
                    test_frame.columnconfigure(0, weight=1)
                    
                    label = ctk.CTkLabel(
                        test_frame,
                        text=f"Template: {preview_text}",
                        anchor="w"
                    )
                    label.pack(side="left", padx=5, fill="x", expand=True)
                    
                    play_btn = ctk.CTkButton(
                        test_frame,
                        text="▶ Play",
                        command=lambda path=test_path: self._play_template_test(path),
                        width=80
                    )
                    play_btn.pack(side="right", padx=5)
                    
                    row += 1
                else:
                    logger.warning(f"Template test audio file not found: {test_path}")
            
            # Add custom tests
            for idx, custom_test in enumerate(custom_tests):
                test_path = custom_test.get("audio_path", "")
                test_text = custom_test.get("text", "")
                
                if Path(test_path).exists():
                    preview_text = test_text[:50] + "..." if len(test_text) > 50 else test_text
                    
                    test_frame = ctk.CTkFrame(test_audio_scroll)
                    test_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
                    test_frame.columnconfigure(0, weight=1)
                    
                    label = ctk.CTkLabel(
                        test_frame,
                        text=f"Custom: {preview_text}",
                        anchor="w"
                    )
                    label.pack(side="left", padx=5, fill="x", expand=True)
                    
                    play_btn = ctk.CTkButton(
                        test_frame,
                        text="▶ Play",
                        command=lambda path=test_path: self._play_template_test(path),
                        width=80
                    )
                    play_btn.pack(side="right", padx=5)
                    
                    row += 1
                else:
                    logger.warning(f"Custom test audio file not found: {test_path}")
        
        # Actions section
        actions_frame = ctk.CTkFrame(self.details_content_frame)
        actions_frame.pack(fill="x", pady=20)
        
        actions_title = ctk.CTkLabel(actions_frame, text="Actions:", font=("Arial", 12, "bold"))
        actions_title.pack(anchor="w", pady=5)
        
        button_frame = ctk.CTkFrame(actions_frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        # Delete button
        delete_btn = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete Voice",
            command=lambda: self._delete_voice(voice),
            fg_color="red",
            hover_color="darkred",
            width=150
        )
        delete_btn.pack(side="left", padx=5)
        
        # Export button
        export_btn = ctk.CTkButton(
            button_frame,
            text="📤 Export",
            command=lambda: self._export_voice(voice),
            width=150
        )
        export_btn.pack(side="left", padx=5)
    
    def _add_metadata_row(self, parent, label: str, value: str) -> None:
        """Add a metadata row to the parent frame.
        
        Args:
            parent: Parent frame
            label: Label text
            value: Value text
        """
        row_frame = ctk.CTkFrame(parent)
        row_frame.pack(fill="x", pady=2)
        
        label_widget = ctk.CTkLabel(row_frame, text=label, font=("Arial", 11, "bold"), width=120, anchor="w")
        label_widget.pack(side="left", padx=5)
        
        value_widget = ctk.CTkLabel(row_frame, text=value, anchor="w")
        value_widget.pack(side="left", padx=5)
    
    def _format_date(self, iso_date: str) -> str:
        """Format ISO date string to readable format.
        
        Args:
            iso_date: ISO format date string
            
        Returns:
            Formatted date string
        """
        try:
            dt = datetime.fromisoformat(iso_date)
            return dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            return iso_date
    
    def _play_template_test(self, audio_path: str) -> None:
        """Play a template test audio file.
        
        Args:
            audio_path: Path to template test audio file
        """
        try:
            from core.audio_utils import load_audio
            
            if Path(audio_path).exists():
                audio_data, sample_rate = load_audio(audio_path)
                
                # Play using the audio player directly
                self.audio_player.play(audio_data, sample_rate)
                
                logger.info(f"Playing template test audio: {audio_path}")
            else:
                logger.warning(f"Template test audio file not found: {audio_path}")
                messagebox.showwarning("File Not Found", f"Template test audio file not found:\n{audio_path}")
        except Exception as e:
            logger.error(f"Failed to play template test audio: {e}")
            # Don't show error dialog to user for playback errors, just log it
            messagebox.showerror("Playback Error", f"Failed to play template test audio:\n{e}")
    
    def _play_reference_audio(self, audio_path: str) -> None:
        """Play reference audio for a cloned voice.
        
        Args:
            audio_path: Path to reference audio file
        """
        try:
            from core.audio_utils import load_audio
            
            if Path(audio_path).exists():
                audio_data, sample_rate = load_audio(audio_path)
                
                # Play using the audio player directly
                self.audio_player.play(audio_data, sample_rate)
                
                logger.info(f"Playing reference audio: {audio_path}")
            else:
                logger.warning(f"Reference audio file not found: {audio_path}")
                messagebox.showwarning("File Not Found", f"Reference audio file not found:\n{audio_path}")
        except Exception as e:
            logger.error(f"Failed to play reference audio: {e}")
            messagebox.showerror("Playback Error", f"Failed to play reference audio:\n{e}")
    
    def _delete_voice(self, voice: dict) -> None:
        """Delete a voice from the library.
        
        Args:
            voice: Voice data dictionary
        """
        response = messagebox.askyesno(
            "Delete Voice",
            f"Are you sure you want to delete '{voice['name']}'?\n\n"
            "This action cannot be undone."
        )
        
        if response:
            success = self.voice_library.delete_voice(voice["id"])
            if success:
                messagebox.showinfo("Success", f"Voice '{voice['name']}' deleted successfully.")
                self._show_empty_details()
                self._refresh_voice_list()
            else:
                messagebox.showerror("Error", f"Failed to delete voice '{voice['name']}'.")
    
    def _export_voice(self, voice: dict) -> None:
        """Export voice data.
        
        Args:
            voice: Voice data dictionary
        """
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            title="Export Voice",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{voice['name']}.json"
        )
        
        if filename:
            try:
                self.voice_library.export_voice(voice["id"], filename)
                messagebox.showinfo("Success", f"Voice '{voice['name']}' exported successfully.")
            except Exception as e:
                logger.error(f"Failed to export voice: {e}")
                messagebox.showerror("Error", f"Failed to export voice:\n{e}")
    
    def refresh(self) -> None:
        """Refresh the voice list (called externally when new voices are added)."""
        self._refresh_voice_list()
        if self.selected_voice:
            # Refresh selected voice details if it still exists
            voice = self.voice_library.get_voice(self.selected_voice["id"])
            if voice:
                self._show_voice_details(voice)
            else:
                self._show_empty_details()
