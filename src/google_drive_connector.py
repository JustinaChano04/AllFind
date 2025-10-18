"""
Google Drive API Connector
Handles authentication and file retrieval from Google Drive folders.
"""

import os
import pickle
from typing import List, Dict, Optional, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveConnector:
    """
    Connector for Google Drive API.
    Handles authentication and provides methods to list and download files.
    """

    def __init__(self, credentials_file: Optional[str] = None):
        """
        Initialize the Google Drive connector.

        Args:
            credentials_file: Path to credentials.json file.
                            If None, uses GOOGLE_CREDENTIALS_FILE from .env
        """
        self.credentials_file = credentials_file or os.getenv(
            'GOOGLE_CREDENTIALS_FILE',
            'credentials.json'
        )
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Drive API using OAuth2."""
        # Token file stores user's access and refresh tokens
        token_file = 'token.json'

        # Load existing credentials if available
        if os.path.exists(token_file):
            self.creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # If no valid credentials, let user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("Refreshing expired credentials...")
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        f"Please download OAuth2 credentials from Google Cloud Console."
                    )
                print("Initiating OAuth2 flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(token_file, 'w') as token:
                token.write(self.creds.to_json())
            print("Authentication successful!")

        # Build the service
        self.service = build('drive', 'v3', credentials=self.creds)

    def list_files_in_folder(
        self,
        folder_id: Optional[str] = None,
        recursive: bool = True,
        file_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List all files in a Google Drive folder.

        Args:
            folder_id: The ID of the folder to list files from.
                      If None, uses GOOGLE_DRIVE_FOLDER_ID from .env or lists from root.
            recursive: If True, includes files from subfolders.
            file_types: List of MIME types to filter (e.g., ['application/pdf']).
                       If None, returns all file types.

        Returns:
            List of file metadata dictionaries containing:
                - id: File ID
                - name: File name
                - mimeType: MIME type
                - size: File size in bytes (if available)
                - createdTime: Creation timestamp
                - modifiedTime: Last modification timestamp
                - webViewLink: Link to view in browser
                - parents: List of parent folder IDs
        """
        if folder_id is None:
            folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

        all_files = []

        try:
            if folder_id:
                # Search within specific folder
                query = f"'{folder_id}' in parents and trashed=false"
            else:
                # Search all files user has access to
                query = "trashed=false"

            # Add MIME type filter if specified
            if file_types:
                mime_queries = " or ".join([f"mimeType='{mt}'" for mt in file_types])
                query += f" and ({mime_queries})"

            # Fetch files
            page_token = None
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, size, '
                           'createdTime, modifiedTime, webViewLink, parents, owners)',
                    pageToken=page_token
                ).execute()

                files = response.get('files', [])
                all_files.extend(files)

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            # If recursive, get files from subfolders
            if recursive:
                folders = [f for f in all_files if f['mimeType'] == 'application/vnd.google-apps.folder']
                for folder in folders:
                    subfolder_files = self.list_files_in_folder(
                        folder_id=folder['id'],
                        recursive=True,
                        file_types=file_types
                    )
                    all_files.extend(subfolder_files)

            print(f"Found {len(all_files)} files")
            return all_files

        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metadata for a specific file.

        Args:
            file_id: The ID of the file

        Returns:
            Dictionary with file metadata or None if error
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, createdTime, modifiedTime, '
                       'webViewLink, parents, owners, description'
            ).execute()
            return file
        except HttpError as error:
            print(f"Error getting file metadata: {error}")
            return None

    def download_file(self, file_id: str, output_path: str) -> bool:
        """
        Download a file from Google Drive.

        Args:
            file_id: The ID of the file to download
            output_path: Path where the file should be saved

        Returns:
            True if successful, False otherwise
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_handle = io.BytesIO()
            downloader = MediaIoBaseDownload(file_handle, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download progress: {int(status.progress() * 100)}%")

            # Write to file
            with open(output_path, 'wb') as f:
                f.write(file_handle.getvalue())

            print(f"Downloaded to {output_path}")
            return True

        except HttpError as error:
            print(f"Error downloading file: {error}")
            return False

    def export_google_doc(
        self,
        file_id: str,
        output_path: str,
        export_format: str = 'text/plain'
    ) -> bool:
        """
        Export a Google Workspace file (Docs, Sheets, Slides) to a specific format.

        Args:
            file_id: The ID of the file to export
            output_path: Path where the exported file should be saved
            export_format: MIME type for export format
                          Common formats:
                          - 'text/plain' for Google Docs
                          - 'application/pdf' for PDF
                          - 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' for .docx
                          - 'text/csv' for Google Sheets

        Returns:
            True if successful, False otherwise
        """
        try:
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType=export_format
            )
            file_handle = io.BytesIO()
            downloader = MediaIoBaseDownload(file_handle, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Export progress: {int(status.progress() * 100)}%")

            # Write to file
            with open(output_path, 'wb') as f:
                f.write(file_handle.getvalue())

            print(f"Exported to {output_path}")
            return True

        except HttpError as error:
            print(f"Error exporting file: {error}")
            return False

    def get_file_content(self, file_id: str, file_mime_type: str) -> Optional[str]:
        """
        Get text content from a file.
        For Google Docs, exports as plain text.
        For other text files, downloads content directly.

        Args:
            file_id: The ID of the file
            file_mime_type: The MIME type of the file

        Returns:
            File content as string, or None if error
        """
        try:
            # Google Docs need to be exported
            if 'google-apps' in file_mime_type:
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            else:
                # Regular files can be downloaded directly
                request = self.service.files().get_media(fileId=file_id)

            file_handle = io.BytesIO()
            downloader = MediaIoBaseDownload(file_handle, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            # Return content as string
            return file_handle.getvalue().decode('utf-8', errors='ignore')

        except HttpError as error:
            print(f"Error getting file content: {error}")
            return None
        except Exception as e:
            print(f"Error decoding file content: {e}")
            return None


# Example usage
if __name__ == "__main__":
    # Initialize connector
    connector = GoogleDriveConnector()

    # Get folder ID from environment or use None for all files
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

    if folder_id:
        print(f"Listing files in folder: {folder_id}")
    else:
        print("No folder ID specified. Listing all accessible files.")

    # List all files
    files = connector.list_files_in_folder(folder_id=folder_id, recursive=True)

    # Print file information
    print("\n" + "="*80)
    print(f"Total files found: {len(files)}")
    print("="*80 + "\n")

    for i, file in enumerate(files, 1):
        print(f"{i}. {file['name']}")
        print(f"   ID: {file['id']}")
        print(f"   Type: {file['mimeType']}")
        print(f"   Link: {file.get('webViewLink', 'N/A')}")
        if 'size' in file:
            size_kb = int(file['size']) / 1024
            print(f"   Size: {size_kb:.2f} KB")
        print()

    # Example: Get content from first text file
    text_files = [
        f for f in files
        if 'google-apps.document' in f['mimeType'] or 'text' in f['mimeType']
    ]

    if text_files:
        print("\n" + "="*80)
        print("Example: Getting content from first document")
        print("="*80 + "\n")

        first_file = text_files[0]
        print(f"Reading: {first_file['name']}")
        content = connector.get_file_content(first_file['id'], first_file['mimeType'])

        if content:
            print("\nFirst 500 characters:")
            print("-" * 80)
            print(content[:500])
            print("-" * 80)
