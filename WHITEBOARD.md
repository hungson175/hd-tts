# WHITEBOARD - Current Sprint

## Team Status (Updated: 03:38)

| Role | Current Task | Status | Notes |
|------|--------------|--------|-------|
| **FS** | UI-001 | DONE | Waveform visualization. Ready for review |
| **DEV** | - | Idle | Fixed hydration error proactively |
| **PO** | Coordination | - | Managing sprints |

---

## Active Tasks

### FS: UI-002 + UI-006 (Frontend Sprint)

**UI-002: Download and Share Buttons**
- Add download button to audio widget → downloads WAV file
- Add share button → copy link or native share API

**UI-006: Remove Redundant Tab**
- Remove "Generated Audio" tab entirely
- Keep right-side audio widget functional

**Deliverables:**
- [ ] Download button works
- [ ] Share button works (copy link)
- [ ] "Generated Audio" tab removed
- [ ] Build passes (Webpack, not Turbopack!)

---

### DEV: TECH-001 - Backend Test Coverage

**Goal:** Add automated tests for backend gateway and worker.

**Scope:**
- Test `/synthesize` endpoint (mock TTS)
- Test `/health` endpoint
- Test job queue operations
- Test API key auth (already has tests, extend if needed)

**Deliverables:**
- [ ] pytest tests in `backend/tests/`
- [ ] 80%+ coverage on gateway
- [ ] All tests pass

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
