from googleapiclient.discovery import build
import logging
import io

logger = logging.getLogger("chief.integrations.google.drive")

def list_files(creds, folder_id=None, query=None, max_results=20):
    """List files in Google Drive, optionally filtered by folder or query."""
    service = build('drive', 'v3', credentials=creds)
    
    # Base query for files (not directories)
    q = "mimeType != 'application/vnd.google-apps.folder'"
    
    if folder_id:
        q += f" and '{folder_id}' in parents"
    if query:
        q += f" and ({query})"
        
    try:
        results = service.files().list(
            q=q,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, createdTime)",
            orderBy="modifiedTime desc"
        ).execute()
        
        items = results.get('files', [])
        return {"files": items}
    except Exception as e:
        logger.error(f"Error listing Drive files: {e}")
        return {"error": str(e)}

def search_files(creds, query):
    """Search for files in Drive."""
    return list_files(creds, query=query)

def read_document(creds, file_id):
    """Read the content of a Google Doc or text file."""
    service = build('drive', 'v3', credentials=creds)
    
    try:
        file_meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        mime_type = file_meta.get('mimeType', '')
        
        # If it's a Google Doc, export it as text
        if mime_type == 'application/vnd.google-apps.document':
            request = service.files().export_media(fileId=file_id, mimeType='text/plain')
            content = request.execute().decode('utf-8')
            return {"content": content, "metadata": file_meta}
        # If it's a plain text file, download it directly
        elif mime_type == 'text/plain':
            request = service.files().get_media(fileId=file_id)
            content = request.execute().decode('utf-8')
            return {"content": content, "metadata": file_meta}
        # If it's a MS Word document (.docx)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            request = service.files().get_media(fileId=file_id)
            file_data = request.execute()
            
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_data))
                content = "\\n".join([paragraph.text for paragraph in doc.paragraphs])
                return {"content": content, "metadata": file_meta}
            except ImportError:
                return {"error": "python-docx library is required to read .docx files.", "metadata": file_meta}
        else:
            return {"error": f"Unsupported file type for direct reading: {mime_type}. Use specific parsers (e.g. PDF) for this type.", "metadata": file_meta}
            
    except Exception as e:
        logger.error(f"Error reading Drive document {file_id}: {e}")
        return {"error": str(e)}
