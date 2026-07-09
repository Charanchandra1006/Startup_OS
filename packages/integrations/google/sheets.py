from googleapiclient.discovery import build
import logging

logger = logging.getLogger("chief.integrations.google.sheets")

def get_sheet_metadata(creds, spreadsheet_id):
    """Fetch metadata about a Google Sheet (tabs, structure)."""
    service = build('sheets', 'v4', credentials=creds)
    
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        titles = [sheet.get("properties", {}).get("title", "") for sheet in sheets]
        return {"titles": titles, "metadata": sheet_metadata}
    except Exception as e:
        logger.error(f"Error fetching sheet metadata: {e}")
        return {"error": str(e)}

def read_spreadsheet(creds, spreadsheet_id, range_name="Sheet1"):
    """Read a specific range from a Google Sheet."""
    service = build('sheets', 'v4', credentials=creds)
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        rows = result.get('values', [])
        
        if not rows:
            return {"rows": [], "headers": []}
            
        headers = rows[0]
        data = rows[1:]
        
        # Convert to a list of dicts for easier processing if headers exist
        structured_data = []
        if headers:
            for row in data:
                # Pad row with empty strings if it's shorter than headers
                row_data = list(row) + [''] * (len(headers) - len(row))
                # Map headers to row values
                structured_data.append(dict(zip(headers, row_data)))
                
        return {
            "headers": headers,
            "rows": structured_data,
            "raw_rows": rows
        }
    except Exception as e:
        logger.error(f"Error reading spreadsheet {spreadsheet_id}: {e}")
        return {"error": str(e)}
