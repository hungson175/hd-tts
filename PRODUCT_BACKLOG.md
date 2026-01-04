# Product Backlog - VietVoice-TTS

## Progress Summary

**Total Items:** 17
**Completed:** 12 (71%)
**In Sprint:** 0 (0%)
**Ready:** 4 (24%)
**New:** 1 (6%)

### Breakdown by Category
- **Voice Cloning:** 3/4 done (75%)
- **UI Features:** 5/7 done (71%)
- **Infrastructure:** 2/2 done (100%)
- **Technical:** 1/3 done (33%)
- **Auth/API:** 1/2 done (50%)

---

## VC-001: Voice Cloning - Recording Support
**Priority:** P1
**Status:** Done

### Description
Wire voice cloning into the system. Implement recording functionality so users can record their voice directly in the browser as reference audio for voice cloning. Provide a default text for user to read (simplifies flow - no manual transcript needed).

### Acceptance Criteria
- [ ] User can record audio in browser
- [ ] Default text displayed for user to read aloud
- [ ] Recorded audio + default text sent to backend
- [ ] TTS uses recorded voice for cloning

---

## VC-004: Save Voice Samples for Reuse
**Priority:** P1
**Status:** Done

### Description
Allow users to save current recording to server for reuse. No need to re-record next time.

### Naming Rules
- **Named saves:** User provides custom name → kept permanently
- **Default saves:** Auto-named "recorded_YYYYMMDD_HHMM" → max 3 kept, oldest discarded

### Acceptance Criteria
- [ ] Save current recording to server
- [ ] Optional: user provides custom name (else auto-name)
- [ ] List user's saved voice samples
- [ ] Select saved sample for voice cloning
- [ ] Named samples: never overwritten
- [ ] Default samples: max 3, auto-discard oldest

---

## VC-002: Voice Cloning - File Upload Support
**Priority:** P1
**Status:** Done

### Description
Voice cloning should support uploading existing audio files. Users can browse and select local files as reference audio.

### Acceptance Criteria
- [ ] User can browse and select local audio files
- [ ] Uploaded file is sent to backend as reference_audio
- [ ] Supported formats: WAV, MP3 (at minimum)

---

## VC-003: Voice Cloning - Unified UI
**Priority:** P1
**Status:** Ready

### Description
UI must support both selection methods - dropdown to choose input method (record/upload) and local file browser for uploads.

### Acceptance Criteria
- [ ] Dropdown to select input method: "Record" or "Upload File"
- [ ] Record mode: shows record button, timer, playback
- [ ] Upload mode: shows file browser, file name display
- [ ] Both modes require reference_text input

---

## UI-001: Audio Waveform Visualization
**Priority:** P1
**Status:** Done

### Description
Current audio visualization uses random sizes and looks messy. Find and integrate a proper library to display the actual audio waveform.

### Acceptance Criteria
- [ ] Use a proper audio waveform library
- [ ] Display actual audio wave shape (not random bars)
- [ ] Looks clean and professional

---

## UI-002: Download and Share Buttons for Audio Widget
**Priority:** P1
**Status:** Ready

### Description
Add download and share icon buttons to the generated audio widget.

### Acceptance Criteria
- [ ] Download button - downloads the audio file
- [ ] Share button - shares the audio (copy link or native share)

---

## UI-003: Linear Progress Bar with Time Estimation
**Priority:** P1
**Status:** Done

### Description
When "Generate Speech" is clicked, show a horizontal progress bar directly below the button. Shows elapsed time and estimated total time based on word count.

### Design Specs
- **Position:** Directly below "Generate Speech" button
- **Width:** Same as button width
- **Fill direction:** Bottom to top
- **Color:** Green
- **Display:** Shows elapsed/estimated time

### Implementation Notes
1. **Calibration (one-time):** Run 3 sample messages, calculate average time per word
2. **Runtime:** Count words in user input → estimate total seconds
3. **Progress bar:** Linear horizontal, fills with green from bottom to top
4. **Display:** Show elapsed seconds and estimated total
5. **Cap at ~95-99%** until actually complete (since it's an estimate)

### Acceptance Criteria
- [ ] Linear progress bar appears below "Generate Speech" button
- [ ] Same width as button
- [ ] Fills green from bottom to top
- [ ] Shows elapsed seconds
- [ ] Shows estimated total time (based on word count)
- [ ] Progress fills smoothly, caps near 100% until done
- [ ] Time-per-word calibrated from 3 sample runs

---

## UI-004: Compact Audio Widget Layout
**Priority:** P1
**Status:** Ready

### Description
The audio widget takes up too much space (entire side). Make it more compact and visually appealing. Could be inline with HD Voice Clone section. Show empty state or sample when nothing generated.

### Acceptance Criteria
- [ ] Widget is more compact, not full-width sidebar
- [ ] Better visual integration with main UI
- [ ] Empty/sample state when no audio generated yet
- [ ] Overall cleaner aesthetics

---

## UI-005: Default Quality to High
**Priority:** P0
**Status:** Done

### Description
Set default quality to "high" instead of "fast". Fast quality is too poor.

### Acceptance Criteria
- [ ] Quality selector defaults to "high"

---

## UI-006: Remove Redundant "Generated Audio" Tab
**Priority:** P1
**Status:** Ready

### Description
The "Generated Audio" tab is redundant - there's already a widget on the right side that shows generated audio. Remove the tab entirely.

### Acceptance Criteria
- [ ] "Generated Audio" tab removed from UI
- [ ] Right-side audio widget remains functional

---

## AUTH-001: User Login System
**Priority:** P0
**Status:** Ready

### Description
Add login/authentication. Track who uses the app (wife, self, friends). Ability to disable accounts if link shared too widely.

### Acceptance Criteria
- [ ] User login/registration
- [ ] Usage tracking per account
- [ ] Ability to disable/block accounts

---

## INFRA-001: Persistent Linux Services
**Priority:** P0
**Status:** Done

### Description
Turn all services (backend gateway, workers, Redis, frontend) into persistent Linux services that survive server restarts. Must be done before Cloudflare deployment.

### Acceptance Criteria
- [ ] Services configured as systemd units (or similar)
- [ ] Auto-start on server boot
- [ ] Survives server restarts

---

## DEPLOY-001: Cloudflare Deployment
**Priority:** P0
**Status:** Done

### Description
Deploy publicly via Cloudflare for wife to use. Expose both frontend and API.

### Domain Configuration
- **Frontend:** hd-tts.hungson175.com
- **Backend:** hd-tts-backend.hungson175.com
- **CNAME target:** a32e099c-a588-46a3-92b8-22689cc157a8.cfargotunnel.com
- **Proxy status:** proxied
- **TTL:** Auto

### IMPORTANT NOTE
Frontend calls backend via **local address** (localhost:17603), NOT the public backend domain. The backend domain (hd-tts-backend.hungson175.com) is for external services/API access only. This project uses Cloudflare tunneling, so frontend→backend is local.

### Acceptance Criteria
- [ ] Frontend accessible at hd-tts.hungson175.com
- [ ] Backend API accessible at hd-tts-backend.hungson175.com
- [ ] Wife can use it

---

## API-001: API Key Support
**Priority:** P1
**Status:** Done

### Description
Support API keys so friends can use the TTS service via API.

### Acceptance Criteria
- [ ] Generate API keys for users
- [ ] API authentication via key
- [ ] Usage tracking per API key

---

## TECH-001: Add Test Coverage
**Priority:** P1
**Status:** New

### Description
Add automated tests for core TTS library and backend.

---

## TECH-002: Fix ESLint
**Priority:** P1
**Status:** New

### Description
Install and configure ESLint for frontend.

---

## UI-007: Persistent Input Text
**Priority:** P1
**Status:** Done

### Description
The main text input field should remember the user's last input. On first visit, show sample text. On subsequent visits, show the last text the user provided.

### Acceptance Criteria
- [ ] First-time users see sample text (default)
- [ ] Returning users see their last input text
- [ ] Text persists across page refreshes
- [ ] Uses localStorage for persistence

---

## TECH-003: CI/CD Pipeline
**Priority:** P2
**Status:** New

### Description
Set up GitHub Actions for automated testing and builds.
