from googleapiclient.discovery import build
import datetime

def read_events(creds, time_min=None, max_results=10):
    service = build('calendar', 'v3', credentials=creds)
    
    if not time_min:
        time_min = datetime.datetime.utcnow().isoformat() + 'Z'
        
    events_result = service.events().list(
        calendarId='primary', timeMin=time_min,
        maxResults=max_results, singleEvents=True,
        orderBy='startTime').execute()
        
    events = events_result.get('items', [])
    return {"events": events}

def create_event(creds, summary, start_time, end_time, attendees=None):
    service = build('calendar', 'v3', credentials=creds)
    
    event = {
      'summary': summary,
      'start': {
        'dateTime': start_time,
        'timeZone': 'UTC',
      },
      'end': {
        'dateTime': end_time,
        'timeZone': 'UTC',
      },
    }
    
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
        
    event = service.events().insert(calendarId='primary', body=event).execute()
    return {"status": "success", "event_id": event.get('id'), "link": event.get('htmlLink')}
