import logging
import json
import requests
from typing import Optional, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GDocsLoader:
    def __init__(self, doc_id: str, credentials_json: Optional[str] = None):
        self.doc_id = doc_id
        self.credentials_json = credentials_json

    def load_text(self) -> str:
        """
        Loads text from the Google Doc.
        Prioritizes Service Account if credentials provided, otherwise tries public export.
        """
        if self.credentials_json:
            try:
                return self._load_via_api()
            except Exception as e:
                logger.error(f"Failed to load via GDocs API: {e}")
                logger.info("Attempting fallback to Drive API export...")
                try:
                    return self._load_via_drive_export()
                except Exception as ex:
                    logger.error(f"Failed to load via Drive API export: {ex}")
                pass

        try:
            text = self._load_via_export()
            if text:
                logger.info("Successfully loaded doc via public export.")
                return text
        except Exception as e:
            logger.warning(f"Failed to load via export link: {e}")
        
        raise ValueError("Could not load document. Ensure it is public, valid credentials are provided, or it is a supported format.")

    def _load_via_export(self) -> str:
        """Downloads the doc as plain text using the export endpoint."""
        url = f"https://docs.google.com/document/d/{self.doc_id}/export?format=txt"
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def _load_via_api(self) -> str:
        """Loads doc using Google Docs API verification."""
        logger.info("Loading document via Google Docs API...")
        
        creds = self._get_creds()
        service = build('docs', 'v1', credentials=creds)
        
        # This will fail for non-native GDocs (e.g. .docx) with 400 Bad Request
        document = service.documents().get(documentId=self.doc_id).execute()
        
        return self._read_structural_elements(document.get('body').get('content'))

    def _load_via_drive_export(self) -> str:
        """
        Fallback: Uses Drive API to export non-native docs (like .docx) to text/plain.
        """
        logger.info("Loading document via Google Drive API export...")
        creds = self._get_creds()
        
        # Note: We need drive.readonly scope for this
        service = build('drive', 'v3', credentials=creds)
        
        # Export file as plain text
        request = service.files().export_media(
            fileId=self.doc_id,
            mimeType='text/plain'
        )
        response = request.execute()
        return response.decode('utf-8')

    def _get_creds(self):
        try:
            creds_dict = json.loads(self.credentials_json)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON")

        return service_account.Credentials.from_service_account_info(
            creds_dict,
            # We add drive.readonly to support the fallback
            scopes=[
                'https://www.googleapis.com/auth/documents.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
        )

    def _read_structural_elements(self, elements: list) -> str:
        """Recursively extracts text from document elements."""
        text = ''
        for value in elements:
            if 'paragraph' in value:
                elements = value.get('paragraph').get('elements')
                for elem in elements:
                    text += self._read_paragraph_element(elem)
            elif 'table' in value:
                table = value.get('table')
                for row in table.get('tableRows'):
                    cells = row.get('tableCells')
                    for cell in cells:
                         text += self._read_structural_elements(cell.get('content'))
            elif 'tableOfContents' in value:
                content = value.get('tableOfContents').get('content')
                text += self._read_structural_elements(content)
        return text

    def _read_paragraph_element(self, element: Dict[str, Any]) -> str:
        """Extracts text from a paragraph element."""
        text_run = element.get('textRun')
        if not text_run:
            return ''
        return text_run.get('content')
