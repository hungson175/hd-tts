# Initialize Agent Role

You are initializing as a member of a multi-agent team.

## Step 1: Detect Your Team

Check the current tmux session name to determine your team:
- **hd-tts**: Compact 2-role team (PO, FS)
- **multilangual-tts**: Full Scrum team (PO, SM, TL, BE, FE, QA)

## Step 2: Read System Documentation

Based on your team, read the workflow:

- **hd-tts**: `docs/tmux/hd-tts/workflow.md`
- **multilangual-tts**: `docs/tmux/multilangual-tts/workflow.md`

## Step 3: Read Your Role Prompt

Based on the role argument `$ARGUMENTS`, read your specific role prompt:

### hd-tts Team (Compact)
- **PO** (Product Owner): `docs/tmux/hd-tts/prompts/PO_PROMPT.md`
- **FS** (Full Stack Developer): `docs/tmux/hd-tts/prompts/FS_PROMPT.md`

### multilangual-tts Team (Full Scrum)
- **PO** (Product Owner): `docs/tmux/multilangual-tts/prompts/PO_PROMPT.md`
- **SM** (Scrum Master): `docs/tmux/multilangual-tts/prompts/SM_PROMPT.md`
- **TL** (Tech Lead): `docs/tmux/multilangual-tts/prompts/TL_PROMPT.md`
- **BE** (Backend Developer): `docs/tmux/multilangual-tts/prompts/BE_PROMPT.md`
- **FE** (Frontend Developer): `docs/tmux/multilangual-tts/prompts/FE_PROMPT.md`
- **QA** (Tester): `docs/tmux/multilangual-tts/prompts/QA_PROMPT.md`

## Step 4: Confirm Your Mission

After reading both files:
1. Confirm your role and responsibilities
2. Verify your communication protocol (use tm-send)
3. Check WHITEBOARD.md for current sprint status
4. Be ready to execute your role

## Step 5: Report Ready

### hd-tts Team
- If you are **FS**: `tm-send PO "FS [HH:MM]: Initialized and ready."`
- If you are **PO**: Just confirm: "PO initialized and ready."

### multilangual-tts Team
- If you are **SM**: Just confirm: "SM initialized and ready for Sprint."
- Otherwise: `tm-send SM "$ARGUMENTS [HH:MM]: Initialized and ready."`
