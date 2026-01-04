# WHITEBOARD - Current Sprint

## Team Status (Updated: 03:36)

| Role | Current Task | Status | Notes |
|------|--------------|--------|-------|
| **FS** | UI-003: Linear Progress Bar | Assigned | See spec below |
| **DEV** | - | Idle | Standing by |
| **PO** | Sprint Planning | Active | Assigned UI-003 to FS |

---

## Current Sprint: UI-003

### UI-003: Linear Progress Bar with Time Estimation
**Priority:** P1
**Owner:** FS

#### Description
When "Generate Speech" is clicked, show a horizontal progress bar directly below the button. Shows elapsed time and estimated total time based on word count.

#### Design Specs
- **Position:** Directly below "Generate Speech" button
- **Width:** Same as button width
- **Fill direction:** Bottom to top
- **Color:** Green
- **Display:** Shows elapsed/estimated time

#### Implementation Notes
1. **Calibration (one-time):** Run 3 sample messages, calculate average time per word
2. **Runtime:** Count words in user input → estimate total seconds
3. **Progress bar:** Linear horizontal, fills with green from bottom to top
4. **Display:** Show elapsed seconds and estimated total
5. **Cap at ~95-99%** until actually complete (since it's an estimate)

#### Acceptance Criteria
- [ ] Linear progress bar appears below "Generate Speech" button
- [ ] Same width as button
- [ ] Fills green from bottom to top
- [ ] Shows elapsed seconds
- [ ] Shows estimated total time (based on word count)
- [ ] Progress fills smoothly, caps near 100% until done
- [ ] Time-per-word calibrated from 3 sample runs

---

## Recently Completed

**UI-007: Persistent Input Text** (commit dfa48ea)
- ✓ localStorage persistence implemented
- ✓ First-time users see sample text
- ✓ Returning users see last input
- ✓ SSR-safe implementation

---

## Session Summary (Jan 5, 2026)

### Completed This Session:
1. **UI-002**: Download button (MP3 format, 128kbps)
2. **UI-006**: Removed redundant "Generated Audio" tab
3. **UI-001**: Waveform visualization (wavesurfer.js)
4. **TECH-001**: Backend test coverage (59 tests, 80% coverage)
5. **Voice persistence**: Selected voice remembered across sessions
6. **Auto-collapse**: Voice cloning section collapses on generate
7. **Audio widget**: Moved below main content
8. **Hydration fix**: SSR/client mismatch resolved
9. **Cloudflare**: Tunnel restarted, both domains working

### Commit:
- **33308a6**: feat: Add voice cloning, MP3 download, waveform visualization
- 20 files changed, 2378 insertions(+), 244 deletions(-)

### Live URLs:
- Frontend: https://hd-tts.hungson175.com ✓
- Backend: https://hd-tts-backend.hungson175.com ✓

---

## Recently Completed

| Task | Owner | Date | Notes |
|------|-------|------|-------|
| VC-004: Save Voice Samples | FS | Jan 4 | Save/list/delete working |
| INFRA-001: Persistent Services | DEV | Jan 4 | *Removed - using background processes instead* |
| DEPLOY-001: Cloudflare | DEV | Jan 4 | hd-tts.hungson175.com live |
| VC-002: File Upload | FS | Jan 4 | Drag & drop upload working |
| Text persistence bug | FS | Jan 5 | Text now persists across tab switches |
| Audio trim feature | FS | Jan 5 | Auto-trim files > 15s |
| Download as WAV | FS | Jan 5 | Button to download recordings as .wav |
| Block M4A uploads | FS | Jan 5 | M4A not supported, clear error message |
| Backend-side trim | FS | Jan 5 | Moved trim logic to backend (pydub) |

---

## Blocked / Waiting

| Issue | Waiting On | Since |
|-------|------------|-------|
| M4A format bug | FS investigation | 01:45 |

---

## Notes
- Systemd services removed (too problematic) - using nohup background processes
- SSH tunnel to MacBook for localhost microphone access
- Voice cloning has 15s max audio limit
