# Google Drive OAuth Setup Guide

This guide will help you set up OAuth authentication to access your private Google Docs without making them publicly shared.

## Prerequisites

- A Google account
- Access to Google Cloud Console

## Setup Steps

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top and select **"New Project"**
3. Enter a project name (e.g., "D&D Session Processor")
4. Click **"Create"**

### 2. Enable the Google Drive API

1. In your new project, go to **APIs & Services > Library**
2. Search for "Google Drive API"
3. Click on "Google Drive API"
4. Click **"Enable"**

### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **"External"** user type (unless you have a Google Workspace account)
3. Click **"Create"**
4. Fill in the required fields:
   - **App name**: D&D Session Processor (or your preferred name)
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
5. Click **"Save and Continue"**
6. On the "Scopes" page, click **"Add or Remove Scopes"**
7. Filter for "Google Drive API" and select:
   - `.../auth/drive.readonly` (View files in your Google Drive)
8. Click **"Update"** and then **"Save and Continue"**
9. On the "Test users" page, click **"Add Users"**
10. Add your Google email address
11. Click **"Save and Continue"**
12. Review and click **"Back to Dashboard"**

### 4. Create OAuth Client Credentials

1. Go to **APIs & Services > Credentials**
2. Click **"Create Credentials"** at the top
3. Select **"OAuth client ID"**
4. For Application type, select **"Desktop app"**
5. Give it a name (e.g., "D&D Processor Desktop Client")
6. Click **"Create"**
7. A dialog will appear with your Client ID and Client Secret
8. Click **"Download JSON"**
9. Save the downloaded file as `gdrive_credentials.json` in your project root directory

**Important:** The file MUST be named exactly `gdrive_credentials.json` and placed in the root of your Video_chunking directory.

### 5. Install Required Dependencies

If you haven't already, install the updated dependencies:

```bash
pip install -r requirements.txt
```

### 6. Authorize the Application

1. Start your Gradio app:
   ```bash
   python app.py
   ```

2. Go to the **"Document Viewer"** tab

3. Click **"Start Authorization"**

4. A URL will appear - click on it (or copy-paste into your browser)

5. Sign in with your Google account

6. You'll see a warning that the app isn't verified - this is expected for test apps
   - Click **"Advanced"**
   - Click **"Go to [Your App Name] (unsafe)"**
   - This is safe because YOU created this app

7. Grant the requested permissions (read-only access to Drive)

8. Google will show you an authorization code

9. Copy the code and paste it into the **"Authorization Code"** field in Gradio

10. Click **"Complete Authorization"**

11. You should see a success message!

## Usage

Once authorized, you can:

1. Navigate to the **"Document Viewer"** tab
2. Paste any Google Doc URL (or just the document ID)
3. Click **"Load Document"**
4. The document content will load - no public sharing required!

## Token Storage

Your authorization token is stored securely in:
```
outputs/gdrive_token.json
```

This file contains your refresh token, which allows the app to maintain access without repeated authorization. Keep this file secure and don't commit it to version control.

## Troubleshooting

### "OAuth credentials file not found"
- Make sure `gdrive_credentials.json` is in the project root directory
- Check that the filename is exactly correct (case-sensitive)

### "Access denied" when loading a document
- Verify you have access to the document in your Google Drive
- Try accessing the document directly in Google Drive to confirm permissions
- Re-authorize if needed by clicking "Revoke Authorization" and starting over

### "Token expired" or similar errors
- The app should auto-refresh tokens, but if issues persist:
- Click "Revoke Authorization"
- Delete `outputs/gdrive_token.json`
- Re-authorize from scratch

### "App not verified" warning during authorization
- This is normal for apps in testing mode
- Click "Advanced" → "Go to [App Name] (unsafe)"
- You created this app, so it's safe to proceed

## Security Notes

- Your credentials file (`gdrive_credentials.json`) contains sensitive information
- Your token file (`outputs/gdrive_token.json`) grants access to your Drive
- Both files are included in `.gitignore` (recommended)
- Never share these files publicly
- The app only requests read-only access to Drive (cannot modify your files)

## Revoking Access

If you want to revoke access at any time:

1. In the app: Click **"Revoke Authorization"** in the Document Viewer tab
2. In Google: Visit [Google Account Permissions](https://myaccount.google.com/permissions)
   - Find your app in the list
   - Click on it and select "Remove Access"

## Optional: Publishing Your App

If you want to use this app without the "unverified" warning:

1. In Google Cloud Console, go to **OAuth consent screen**
2. Click **"Publish App"**
3. Note: This requires Google verification if you want users outside your domain

For personal use, keeping it in "Testing" mode is perfectly fine.
