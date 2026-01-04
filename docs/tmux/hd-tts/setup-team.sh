#!/bin/bash

# HD-TTS Compact Team - Automated Setup Script
# Creates a tmux session with 3 Claude Code instances (PO, DEV, FS)

set -e  # Exit on error

PROJECT_ROOT="/home/hungson175/dev/ultimate-boss-HD/VietVoice-TTS"
SESSION_NAME="hd-tts"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting HD-TTS Compact Team Setup..."
echo "Project Root: $PROJECT_ROOT"
echo "Session Name: $SESSION_NAME"

# 1. Check if session already exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session '$SESSION_NAME' already exists!"
    read -p "Kill existing session and create new one? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        tmux kill-session -t $SESSION_NAME
        echo "Killed existing session"
    else
        echo "Aborted. Use 'tmux attach -t $SESSION_NAME' to attach"
        exit 0
    fi
fi

# 2. Verify tm-send is installed globally
echo "Verifying tm-send installation..."
if command -v tm-send >/dev/null 2>&1; then
    echo "tm-send is installed at: $(which tm-send)"
else
    echo ""
    echo "ERROR: tm-send is not installed!"
    echo ""
    echo "tm-send is a GLOBAL tool that must be installed to ~/.local/bin/tm-send"
    echo "Install it first, then re-run this script."
    echo ""
    exit 1
fi

# 3. Start new tmux session
echo "Creating tmux session '$SESSION_NAME'..."
cd "$PROJECT_ROOT"
tmux new-session -d -s $SESSION_NAME

# 4. Create 3-pane layout (PO | DEV | FS)
echo "Creating 3-pane layout..."
tmux split-window -h -t $SESSION_NAME
tmux split-window -h -t $SESSION_NAME
tmux select-layout -t $SESSION_NAME even-horizontal

# 5. Resize for proper pane widths
echo "Resizing window..."
tmux resize-window -t $SESSION_NAME -x 500 -y 50

# 6. Set pane titles and role names
echo "Setting role names..."
tmux select-pane -t $SESSION_NAME:0.0 -T "PO"
tmux select-pane -t $SESSION_NAME:0.1 -T "DEV"
tmux select-pane -t $SESSION_NAME:0.2 -T "FS"

tmux set-option -p -t $SESSION_NAME:0.0 @role_name "PO"
tmux set-option -p -t $SESSION_NAME:0.1 @role_name "DEV"
tmux set-option -p -t $SESSION_NAME:0.2 @role_name "FS"

# 7. Get pane IDs
echo "Getting pane IDs..."
PANE_IDS=$(tmux list-panes -t $SESSION_NAME -F "#{pane_id}")
PO_PANE=$(echo "$PANE_IDS" | sed -n '1p')
DEV_PANE=$(echo "$PANE_IDS" | sed -n '2p')
FS_PANE=$(echo "$PANE_IDS" | sed -n '3p')

echo "Pane IDs:"
echo "  PO  (Pane 0): $PO_PANE"
echo "  DEV (Pane 1): $DEV_PANE"
echo "  FS  (Pane 2): $FS_PANE"

# 8. Start Claude Code in each pane
echo "Starting Claude Code in all panes..."
tmux send-keys -t $SESSION_NAME:0.0 "cd $PROJECT_ROOT && claude" C-m
tmux send-keys -t $SESSION_NAME:0.1 "cd $PROJECT_ROOT && claude" C-m
tmux send-keys -t $SESSION_NAME:0.2 "cd $PROJECT_ROOT && claude" C-m

# 9. Wait for Claude Code to start
echo "Waiting 25 seconds for Claude Code instances..."
sleep 25

# 10. Initialize roles (Two-Enter Rule + 0.3s sleep)
echo "Initializing agent roles..."
tmux send-keys -t $SESSION_NAME:0.0 "/init-role PO" C-m
sleep 0.3
tmux send-keys -t $SESSION_NAME:0.0 C-m
sleep 2
tmux send-keys -t $SESSION_NAME:0.1 "/init-role DEV" C-m
sleep 0.3
tmux send-keys -t $SESSION_NAME:0.1 C-m
sleep 2
tmux send-keys -t $SESSION_NAME:0.2 "/init-role FS" C-m
sleep 0.3
tmux send-keys -t $SESSION_NAME:0.2 C-m

# 11. Wait for initialization
echo "Waiting 20 seconds for role initialization..."
sleep 20

# 12. Summary
echo ""
echo "Setup Complete!"
echo ""
echo "Session: $SESSION_NAME"
echo "Project: $PROJECT_ROOT"
echo ""
echo "HD-TTS Compact Team:"
echo "  +--------+--------+--------+"
echo "  | PO     | DEV    | FS     |"
echo "  | Pane 0 | Pane 1 | Pane 2 |"
echo "  +--------+--------+--------+"
echo ""
echo "Roles:"
echo "  - PO:  Product Owner (backlog, docs, priorities)"
echo "  - DEV: Developer (parallel coding tasks)"
echo "  - FS:  Full Stack Developer (main coding)"
echo ""
echo "Next steps:"
echo "  1. Attach: tmux attach -t $SESSION_NAME"
echo "  2. Boss provides Sprint Goal to PO"
echo "  3. Team executes Sprint"
echo ""
echo "Boss communication (from separate terminal):"
echo "  tmux send-keys -t $SESSION_NAME:0.0 'BOSS [HH:MM]: message' C-m"
echo "  sleep 0.3 && tmux send-keys -t $SESSION_NAME:0.0 C-m"
echo ""
echo "To detach: Ctrl+B, then D"
echo "To kill: tmux kill-session -t $SESSION_NAME"
echo ""

# 13. Move cursor to PO pane
tmux select-pane -t $SESSION_NAME:0.0
echo "Cursor in Pane 0 (PO)."
