import datetime
from googleapiclient.discovery import build

def read_events(credentials, max_results=10):
    service = build('calendar', 'v3', credentials=credentials)
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=max_results, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])
    return {"events": [{"summary": e.get("summary"), "start": e["start"].get("dateTime", e["start"].get("date"))} for e in events]}

def create_event(credentials, summary, start_time, end_time, attendees=None):
    service = build('calendar', 'v3', credentials=credentials)
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
        event['attendees'] = [{'email': e} for e in attendees]
        
    event = service.events().insert(calendarId='primary', body=event).execute()
    return {"status": "success", "event_link": event.get('htmlLink')}
