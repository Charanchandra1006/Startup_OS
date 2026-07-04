from googleapiclient.discovery import build

def read_emails(credentials, max_results=5):
    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    emails = []
    if not messages:
        return {"emails": []}
        
    for msg in messages:
        txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = txt.get('snippet')
        emails.append({"id": msg['id'], "snippet": snippet})
    return {"emails": emails}

def draft_email(credentials, to, subject, body):
    # Draft an email (Mock logic for Phase 1 safety, real API requires email.mime)
    return {"status": "success", "message": "Email drafted successfully (mock)", "details": f"Drafted to {to}"}

def send_email(credentials, to, subject, body):
    # Send email (Mock logic for Phase 1 safety)
    return {"status": "success", "message": "Email sent successfully (mock)", "details": "Real SMTP sending disabled for Phase 1 safety."}
