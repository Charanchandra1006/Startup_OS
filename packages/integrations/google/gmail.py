import base64
from email.message import EmailMessage
from googleapiclient.discovery import build

def read_emails(creds, max_results=10, query="is:unread"):
    service = build('gmail', 'v1', credentials=creds)
    
    results = service.users().messages().list(userId='me', maxResults=max_results, q=query).execute()
    messages = results.get('messages', [])
    
    emails = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        
        # Parse headers
        headers = msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        
        snippet = msg.get('snippet', '')
        
        emails.append({
            'id': message['id'],
            'subject': subject,
            'from': sender,
            'snippet': snippet
        })
        
    return {"emails": emails}

def _create_message(to, subject, body):
    message = EmailMessage()
    message.set_content(body)
    message['To'] = to
    message['From'] = 'me'
    message['Subject'] = subject
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': encoded_message}

def draft_email(creds, to, subject, body):
    service = build('gmail', 'v1', credentials=creds)
    raw_msg = _create_message(to, subject, body)
    
    draft = service.users().drafts().create(userId='me', body={'message': raw_msg}).execute()
    return {"status": "success", "draft_id": draft.get('id')}

def send_email(creds, to, subject, body):
    service = build('gmail', 'v1', credentials=creds)
    raw_msg = _create_message(to, subject, body)
    
    message = service.users().messages().send(userId='me', body=raw_msg).execute()
    return {"status": "success", "message_id": message.get('id')}
