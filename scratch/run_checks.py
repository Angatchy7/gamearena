import sys
import os
import django

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.management import call_command
from io import StringIO

print("========================================")
print("1. RUNNING DJANGO SYSTEM CHECK...")
print("========================================")
try:
    call_command("check")
    print("DJANGO CHECK SUCCESSFUL!")
except Exception as e:
    print(f"DJANGO CHECK ERROR: {e}")

print("\n========================================")
print("2. RUNNING MAKEMIGRATIONS CHECK...")
print("========================================")
try:
    call_command("makemigrations", check=True, dry_run=True)
    print("MAKEMIGRATIONS CHECK SUCCESSFUL (No unmigrated changes)!")
except Exception as e:
    print(f"MAKEMIGRATIONS CHECK RESULT: {e}")

print("\n========================================")
print("3. RUNNING FOCUSED NEW TESTS...")
print("========================================")
try:
    call_command("test", "apps.teams.tests_multi_team", "apps.accounts.tests_password_recovery", verbosity=2)
    print("FOCUSED TESTS PASSED!")
except Exception as e:
    print(f"FOCUSED TESTS RESULT: {e}")

print("\n========================================")
print("4. RUNNING FULL TEST SUITE...")
print("========================================")
try:
    call_command("test", verbosity=2)
    print("FULL TEST SUITE COMPLETED!")
except Exception as e:
    print(f"FULL TEST SUITE RESULT: {e}")
