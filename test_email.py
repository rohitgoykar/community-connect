import smtplib
import os
import sys

def load_env():
    for fpath in ['.env', os.path.join('FinalCode', '.env')]:
        if os.path.isfile(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env()

EMAIL = os.environ.get("EMAIL_ADDRESS", "oopj435@gmail.com").strip()
PASSWORD = os.environ.get("EMAIL_PASSWORD", "dqsnzbjvuawgxyaw").replace(" ", "").strip()

print("=" * 60)
print(f"Testing Gmail SMTP connection for: {EMAIL}")
print("=" * 60)

try:
    print("1. Connecting to smtp.gmail.com:587...")
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
    server.ehlo()
    server.starttls()
    server.ehlo()

    print("2. Authenticating with Gmail...")
    server.login(EMAIL, PASSWORD)
    print(">> SUCCESS! Gmail SMTP authenticated successfully.")
    
    recipient = sys.argv[1] if len(sys.argv) > 1 else EMAIL
    print(f"3. Sending test verification message to: {recipient}...")
    from email.mime.text import MIMEText
    msg = MIMEText(f"Hello! This is a test OTP verification from Smart Community.\nYour test OTP is: 123456")
    msg['Subject'] = "Smart Community - SMTP Test Pass"
    msg['From'] = EMAIL
    msg['To'] = recipient
    server.send_message(msg)
    server.quit()
    print(f">> Delivered test email to {recipient}!")

except smtplib.SMTPAuthenticationError as e:
    print("\n[FAILED] Gmail rejected the credentials (535 Bad Credentials).")
    print("Google requires a 16-character App Password generated from:")
    print("https://myaccount.google.com/apppasswords")
    print(f"Error details: {e}")

except Exception as e:
    print(f"\n[FAILED] {type(e).__name__}: {e}")
    print("Check if EMAIL_ADDRESS and EMAIL_PASSWORD in .env are active.")