#!/bin/bash
# Script de deploy em massa

# Escola 1
python manage.py create_school --name "Escola A" --schema "escola_a" --domain "a.sotarq.school" --type "k12" --color "#1a73e8" --admin-email "dir@a.com" --admin-pass "123"

# Escola 2
python manage.py create_school --name "Escola B" --schema "escola_b" --domain "b.sotarq.school" --type "creche" --color "#e11d48" --admin-email "dir@b.com" --admin-pass "123"

# ... repita 100 vezes ...