import os
import json
import smtplib
import requests
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone

CONFIG_FILE = "config.json"
CSV_PATH = "conjunction-warning.csv"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

class NotifyAgent:
    def __init__(self):
        self.config = load_config()
        self.email_cfg = self.config.get("email", {})
        self.slack_cfg = self.config.get("slack", {})

    def _has_danger(self, threshold_km=2.0):
        """CSV'yi kontrol eder ve kritik bir yakınlaşma olup olmadığını döner."""
        if not os.path.exists(CSV_PATH):
            return False, 0, []
        try:
            df = pd.read_csv(CSV_PATH)
            critical_df = df[df['distance_km'] < threshold_km]
            critical_count = len(critical_df)
            involved_sats = list(set(critical_df['satellite_1'].tolist() + critical_df['satellite_2'].tolist()))
            return critical_count > 0, critical_count, involved_sats
        except Exception:
            return False, 0, []

    def send_email_report(self, is_urgent=False):
        """E-posta raporu gönderir. CSV dosyasını ekler."""
        if not self.email_cfg.get("sender_email"):
            print("⚠️ NotifyAgent: Email credentials missing.")
            return

        subject = "🚨 URGENT: Satellite Collision Risk Detected!" if is_urgent else "📊 Hourly Satellite Operations Report"
        body = "Commander,\n\nPlease find the latest satellite conjunction analysis attached."
        if is_urgent:
            body = "⚠️ CRITICAL ALERT: Potential close approaches detected in orbit. Review the attached CSV immediately!"

        msg = MIMEMultipart()
        msg['From'] = self.email_cfg.get("sender_email")
        msg['To'] = self.email_cfg.get("receiver_email")
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # CSV Attachment
        if os.path.exists(CSV_PATH):
            with open(CSV_PATH, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(CSV_PATH)}")
                msg.attach(part)

        try:
            server = smtplib.SMTP(self.email_cfg.get("smtp_server"), self.email_cfg.get("smtp_port"))
            server.starttls()
            server.login(self.email_cfg.get("sender_email"), self.email_cfg.get("sender_password"))
            server.send_message(msg)
            server.quit()
            print(f"✅ NotifyAgent: Email report sent (Urgent: {is_urgent})")
        except Exception as e:
            print(f"❌ NotifyAgent: Email failed: {e}")

    def send_slack_alert(self, critical_count, involved_sats=None):
        """Slack üzerinden uyarı gönderir."""
        webhook_url = self.slack_cfg.get("webhook_url")
        if not webhook_url or "XXXX" in webhook_url:
            print("⚠️ NotifyAgent: Slack webhook missing.")
            return

        sat_text = f"those *{', '.join(involved_sats)}*" if involved_sats else "various"
        payload = {
            "text": f"🚨 *CRITICAL SATELLITE ALERT* 🚨\nDetecting *{critical_count}* high-risk conjunction events {sat_text} satellites. Please review the satellite-orbit-tools dashboard.",
            "attachments": [
                {
                    "text": "Critical conjunction analysis is ready. Please review the satellite-orbit-tools dashboard immediately.",
                    "color": "#ff4d4d",
                    "footer": "Guardian Agent | Autonomous Ops"
                }
            ]
        }

        try:
            requests.post(webhook_url, json=payload, timeout=10)
            print("✅ NotifyAgent: Slack alert sent.")
        except Exception as e:
            print(f"❌ NotifyAgent: Slack failed: {e}")

    def run_check(self):
        """Ajanın ana döngüsü: Tehlikeyi kontrol et ve gerekirse her iki kanaldan uyar."""
        danger_found, count, involved = self._has_danger()
        if danger_found:
            print(f"🔥 NotifyAgent: Danger detected! Sending alerts...")
            self.send_email_report(is_urgent=True)
            self.send_slack_alert(count, involved)
        else:
            # Sadece saatlik rapor (bu fonksiyon çağrıldığında)
            self.send_email_report(is_urgent=False)

    def send_manual_report(self, satellites):
        """Kullanıcı butona bastığında anlık uydu listesini gönderir."""
        sat_list_str = "\n".join([f"• {s['name']} (NORAD: {s['norad_id']})" for s in satellites])
        
        # Email
        subject = "🔄 Manual System Sync: Satellite Asset List"
        body = f"Commander,\n\nA manual system refresh was triggered. Current tracked assets:\n\n{sat_list_str}\n\nOperation status: NOMINAL"
        
        # Reuse existing email logic with manual content
        msg = MIMEMultipart()
        msg['From'] = self.email_cfg.get("sender_email")
        msg['To'] = self.email_cfg.get("receiver_email")
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(self.email_cfg.get("smtp_server"), self.email_cfg.get("smtp_port"))
            server.starttls()
            server.login(self.email_cfg.get("sender_email"), self.email_cfg.get("sender_password"))
            server.send_message(msg)
            server.quit()
        except Exception: pass

        # Slack
        webhook_url = self.slack_cfg.get("webhook_url")
        if webhook_url and "XXXX" not in webhook_url:
            payload = {
                "text": f"🔄 *Manual System Refresh*\nCommander, I am now tracking *{len(satellites)}* assets:\n{sat_list_str}"
            }
            try: requests.post(webhook_url, json=payload, timeout=10)
            except Exception: pass

if __name__ == "__main__":
    # Manuel test için
    agent = NotifyAgent()
    agent.run_check()
