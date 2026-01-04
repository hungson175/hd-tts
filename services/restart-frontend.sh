#!/bin/bash
source ~/dev/.env
echo "$SUDO_PASS" | sudo -S systemctl restart vietvoice-frontend.service
