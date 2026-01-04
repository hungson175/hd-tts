# WHITEBOARD - Current Sprint

## Completed
- **VC-004: Save Voice Samples for Reuse** ✅

## In Progress
- **INFRA-001: Persistent Linux Services** (DEV working)

---

## VC-004 Summary
- Save/list/delete voice samples working
- Frontend save UI with optional naming
- Backend stores in `backend/voice_samples/`
- Root cause of initial failure: Gateway running old code (needed restart)

---

## INFRA-001 Spec (DEV)
- Systemd services for: Frontend, Backend Gateway, Workers, Redis
- Auto-start on boot
- Setup script to install/manage services
- Env file for sudo (added to .gitignore)

---

## Team Status

| Role | Task | Status |
|------|------|--------|
| FS | VC-004 | ✅ Done |
| DEV | INFRA-001 | Working |
