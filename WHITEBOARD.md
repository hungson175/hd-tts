# WHITEBOARD - Current Sprint

## Team Status (Updated: 03:39)

| Role | Current Task | Status | Notes |
|------|--------------|--------|-------|
| **FS** | - | Idle | UI-003 complete (9b76b32) |
| **DEV** | - | Idle | Standing by |
| **PO** | - | Idle | Sprint complete |

---

## Recently Completed

**UI-003: Linear Progress Bar** (commits 9b76b32, de61df6, f08f637)
- ✓ Horizontal bar below Generate button
- ✓ Green fill from bottom to top
- ✓ Time estimation calibrated with real data
- ✓ Smooth animation, caps at 95%
- ✓ Calibration script for future adjustments
- ✓ Fixed: TIME_PER_WORD now includes MP3 conversion overhead (0.27s/word)

**UI-007: Persistent Input Text** (commit dfa48ea)
- ✓ localStorage persistence implemented
- ✓ First-time users see sample text
- ✓ Returning users see last input
- ✓ SSR-safe implementation
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
