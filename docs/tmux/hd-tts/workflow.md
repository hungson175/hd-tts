# HD-TTS Compact Team (3 Roles)

<context>
A minimal 3-agent team for VietVoice-TTS development.
PO handles documents/backlog, FS and DEV handle coding (parallel tasks).
Communication via tm-send in tmux session "hd-tts".
</context>

---

## Team Structure

| Role | Pane | Purpose |
|------|------|---------|
| PO | 0 | Product Owner - backlog, docs, priorities, specs |
| DEV | 1 | Developer - parallel coding tasks (assigned by PO) |
| FS | 2 | Full Stack Developer - main coding (backend + frontend) |
| Boss | Outside | Human user - provides goals, reviews sprints |

**Note:** PO works with FS by default. When FS is busy, Boss can direct PO to assign tasks to DEV for parallel work.

---

## CRITICAL: Pane Detection (Common Bug)

**NEVER use `tmux display-message -p '#{pane_index}'`** - returns cursor pane, NOT your pane!

**Always use $TMUX_PANE:**
```bash
echo $TMUX_PANE
tmux list-panes -a -F '#{pane_id} #{pane_index} #{@role_name}' | grep $TMUX_PANE
```

---

## Communication Protocol

### Use tm-send for ALL Messages

```bash
# Correct - use tm-send with role name
tm-send PO "FS -> PO: Task complete. See commit abc123."
tm-send FS "PO -> FS: New sprint assigned. See WHITEBOARD.md"

# FORBIDDEN - never use raw tmux send-keys
tmux send-keys -t %16 "message" C-m C-m  # NEVER!
```

### Two-Step Response Rule (CRITICAL)

**Every task requires TWO responses:**

1. **ACKNOWLEDGE** (immediately): "Received, starting now"
2. **COMPLETE** (when done): "Task DONE. [Summary]"

```bash
# Step 1: Receive task → IMMEDIATELY acknowledge
tm-send PO "FS -> PO [14:00]: Received sprint task. Starting now."

# Step 2: Complete task → Report completion
tm-send PO "FS -> PO [14:30]: Sprint DONE. 3 commits pushed. Tests passing."
```

### AI-to-AI Communication (MANDATORY)

**THIS IS AN AI TEAM. OTHER AGENTS CANNOT SEE YOUR TERMINAL.**

1. Task Complete → IMMEDIATELY tm-send report
2. Blocked/Waiting → IMMEDIATELY tm-send status
3. Need Something → IMMEDIATELY tm-send request

**SIMPLE RULE: If you want something, SAY IT via tm-send.**
**If you don't communicate, the ENTIRE TEAM gets stuck.**

---

## Sprint Workflow

### Phase 1: Sprint Planning (PO leads)
```
Boss → PO: Sprint Goal
PO: Creates spec in WHITEBOARD.md
PO → FS: Sprint assigned, see WHITEBOARD.md
```

### Phase 2: Sprint Execution (FS leads)
```
FS: Implements with TDD
FS: Commits progressively
FS ↔ PO: Clarifications via tm-send
FS → PO: Sprint complete, ready for review
```

### Phase 3: Sprint Review (PO leads)
```
PO: Verifies implementation against spec
PO → Boss: Sprint summary ready
Boss: Reviews and provides feedback
```

---

## Key Files

| File | Owner | Purpose |
|------|-------|---------|
| WHITEBOARD.md | PO | Current sprint status, specs |
| PRODUCT_BACKLOG.md | PO | All backlog items |
| Code files | FS/DEV | Implementation |

---

## Git Workflow

```bash
# FS commits progressively during sprint
git add -A && git commit -m "feat: description"

# After Boss accepts sprint
git push origin master
```

---

## Boss Terminal

Boss operates from a **separate terminal outside the tmux session**.

**>>> PREFIX**: When Boss types `>>> [message]`, send to PO:
```bash
tmux send-keys -t hd-tts:0.0 "BOSS [HH:MM]: message" C-m
sleep 0.3
tmux send-keys -t hd-tts:0.0 C-m
```

---

## Definition of Done

A Story is "Done" when:
- [ ] Code implemented and committed
- [ ] Tests pass
- [ ] Lint and build pass
- [ ] PO accepts

---

## Common Mistakes

| Mistake | Correct |
|---------|---------|
| Using raw tmux send-keys | Use tm-send |
| Not reporting task completion | ALWAYS report via tm-send |
| Waiting silently | Communicate status immediately |
| Skipping TDD | Write tests first |
