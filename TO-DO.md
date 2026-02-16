# Qwen-semble TO-DO List

## Personal Priority Items

- [ ] Make segment selector panel look and feel like speaker version
- [ ] Remove presets
- [ ] Create a "first run" flag
- [ ] Work on operations conducted in "first run"

---

## Major Improvements

### Core Functionality
- [ ] **Project Save/Load System**
  - Save entire narration state (transcript, mode, voice assignments, segments)
  - Allow reopening and editing previous narrations
  - Auto-save drafts periodically

- [ ] **Batch Processing**
  - Process multiple transcript files in one operation
  - Queue system for background generation
  - Batch export with naming templates

- [ ] **Voice Training Interface**
  - Guided workflow for creating custom voices
  - Voice quality validation before saving
  - Training progress feedback

- [ ] **Multi-Language Support**
  - Add language selection for voices and narrations
  - Support for non-English TTS models
  - Language auto-detection from transcript

- [ ] **Export/Import Voice Library**
  - Backup and restore entire voice library
  - Share voice collections between users
  - Import voice packs from community

### User Experience
- [ ] **Template System**
  - Save common narration patterns as templates
  - Quick-start templates (audiobook, dialogue, documentary, etc.)
  - Template sharing and import

- [ ] **Undo/Redo System**
  - Revert voice assignments
  - Undo transcript edits
  - History panel showing recent actions

- [ ] **Audio Post-Processing**
  - Normalize volume across segments
  - Add background music/ambiance
  - Crossfade between segments
  - Noise reduction and enhancement

### Advanced Features
- [ ] **Voice Preview System**
  - Auto-generate preview samples for all voices
  - Preview voices in context (with actual transcript text)
  - A/B comparison of different voices

- [ ] **Collaborative Features**
  - Export narration projects for sharing
  - Import voice assignments from others
  - Cloud sync for voice library (optional)

- [ ] **Analytics Dashboard**
  - Track voice usage statistics
  - Monitor generation success rates
  - Time spent per narration
  - Model performance metrics

---

## Minor Improvements

### UI/UX Enhancements
- [ ] **Keyboard Shortcuts**
  - Ctrl+O: Load transcript
  - Ctrl+S: Save project
  - Ctrl+G: Generate narration
  - F5: Refresh voice library
  - Ctrl+P: Parse text area

- [ ] **Theme Customization**
  - Dark/light mode toggle
  - Custom accent colors
  - Font size adjustments
  - High contrast mode for accessibility

- [ ] **Drag-and-Drop Support**
  - Drop transcript files directly into text area
  - Drop audio files for voice cloning
  - Drop multiple files for batch processing

- [ ] **Recent Files Menu**
  - Quick access to recently loaded transcripts
  - Recently used voices pinned to top
  - Recent narration output folders

### Voice Management
- [ ] **Voice Organization**
  - Favorites/pinning system for frequently used voices
  - Custom tags beyond default system
  - Voice search by description/characteristics
  - Sort by usage count, date created, name

- [ ] **Voice Operations**
  - Rename voices after creation
  - Duplicate voice for variants
  - Bulk delete with selection
  - Archive unused voices (hide without deleting)

- [ ] **Voice Library Enhancements**
  - Grid view vs list view toggle
  - Voice card size adjustment
  - Filter by multiple tags simultaneously
  - Quick preview on hover

### Transcript Editor
- [ ] **Editor Features**
  - Line numbers in text area
  - Syntax highlighting for [Speaker]: annotations
  - Find and replace functionality
  - Word count live update
  - Spell check integration

- [ ] **Segment Preview**
  - Show segment boundaries visually in text area
  - Highlight current segment being edited
  - Preview segment audio before full generation
  - Edit segment text inline

### Generation & Output
- [ ] **Generation Options**
  - Save generation settings as presets
  - Quick retry failed segments
  - Generate only selected segments
  - Pause and resume generation

- [ ] **Output Management**
  - Copy output file path to clipboard
  - Open output folder button
  - Auto-play on completion option
  - Export transcript with timestamps

### Workspace & Settings
- [ ] **Workspace Improvements**
  - Multiple workspace support
  - Workspace templates
  - Import/export workspace settings
  - Workspace backup utility

- [ ] **Configuration**
  - Import/export app settings
  - Reset to defaults option
  - Advanced settings panel for power users
  - Model path configuration

### Quality of Life
- [ ] **Progress & Feedback**
  - Estimated time remaining for generation
  - Detailed error messages with suggestions
  - Success notifications with sound (optional)
  - Generation history log viewer

- [ ] **Audio Playback**
  - Waveform visualization for generated audio
  - Playback speed control
  - Loop segment playback
  - Compare different voice outputs

- [ ] **Help & Documentation**
  - In-app tutorial/walkthrough
  - Tooltips on complex features
  - Example transcripts for each mode
  - Video tutorials linking

---

## Bug Fixes & Polish

- [ ] Validate all file paths before operations
- [ ] Handle very long transcripts (1000+ segments) gracefully
- [ ] Improve error recovery when GPU runs out of memory
- [ ] Add progress indication for model loading
- [ ] Prevent duplicate voice names in library
- [ ] Handle special characters in filenames properly
- [ ] Optimize memory usage during batch generation
- [ ] Add cancellation points in long operations
- [ ] Improve startup time on first launch
- [ ] Cache model loading for faster subsequent generations

---

## Technical Debt

- [ ] Separate UI code from business logic more clearly
- [ ] Add comprehensive unit tests
- [ ] Add integration tests for generation pipeline
- [ ] Implement proper logging levels throughout
- [ ] Create API documentation for core modules
- [ ] Refactor voice library to use database instead of JSON
- [ ] Implement proper configuration validation
- [ ] Add type hints consistently across codebase
- [ ] Create developer documentation
- [ ] Set up CI/CD pipeline for testing

---

## Future Considerations

- [ ] Plugin system for custom TTS models
- [ ] REST API for remote generation
- [ ] CLI interface for scripting
- [ ] Docker container for easy deployment
- [ ] Web interface alternative to desktop app
- [ ] Mobile companion app (monitoring only)
- [ ] Integration with popular writing tools
- [ ] Voice marketplace/sharing platform
- [ ] Real-time preview during editing
- [ ] AI-assisted voice assignment suggestions
