# Google OAuth Setup - Simple Guide

**Goal:** Get a file called `gdrive_credentials.json` so you can access your private Google Docs.

**Time needed:** 5-10 minutes

**Cost:** Free (no billing required!)

---

## Step 1: Go to Google Cloud Console

1. Open your browser and go to: **https://console.cloud.google.com/**
2. Sign in with your Google account if needed

---

## Step 2: Create or Select a Project

### If you already have a project:
- Click the **project dropdown** at the very top of the page (next to "Google Cloud")
- Select your existing project
- **Skip to Step 3**

### If you need to create a new project:
1. Click the **project dropdown** at the very top (it might say "Select a project")
2. Click **"NEW PROJECT"** in the dialog that appears
3. Enter a project name (anything you want, like "D&D Session Processor")
4. Click **"CREATE"**
5. Wait a few seconds for it to create
6. Make sure your new project is selected (check the project name at the top)

---

## Step 3: Enable the Google Drive API

1. In the left sidebar, click **"APIs & Services"** → **"Library"**
   - (If you don't see the sidebar, click the ☰ hamburger menu at top-left)

2. In the search box at the top, type: **Google Drive API**

3. Click on **"Google Drive API"** in the results

4. Click the blue **"ENABLE"** button

5. Wait a few seconds for it to enable

---

## Step 4: Configure OAuth Consent Screen

This tells Google who you are and what your app does.

1. In the left sidebar, click **"APIs & Services"** → **"OAuth consent screen"**

2. Select **"External"** as the User Type
   - (Even though it says "External", you're the only user)

3. Click **"CREATE"**

4. Fill in the form:
   - **App name:** `D&D Session Processor` (or anything you want)
   - **User support email:** Select your email from the dropdown
   - **Developer contact information:** Enter your email address
   - **Leave everything else blank or default**

5. Click **"SAVE AND CONTINUE"**

6. On the "Scopes" page:
   - Click **"ADD OR REMOVE SCOPES"**
   - In the filter box, type: **drive.readonly**
   - Check the box next to: **".../auth/drive.readonly"** (View files in your Google Drive)
   - Click **"UPDATE"** at the bottom
   - Click **"SAVE AND CONTINUE"**

7. On the "Test users" page:
   - Click **"+ ADD USERS"**
   - Enter your Google email address
   - Click **"ADD"**
   - Click **"SAVE AND CONTINUE"**

8. On the "Summary" page:
   - Review and click **"BACK TO DASHBOARD"**

**Important:** Keep your app in "Testing" mode - don't publish it! Testing mode is free and works perfectly.

---

## Step 5: Create OAuth Credentials (The Important Part!)

This creates the file you need.

1. In the left sidebar, click **"APIs & Services"** → **"Credentials"**

2. At the top, click **"+ CREATE CREDENTIALS"**

3. Select **"OAuth client ID"**

4. For "Application type", select **"Desktop app"**

5. Give it a name: `D&D Desktop Client` (or anything you want)

6. Click **"CREATE"**

7. A popup appears saying "OAuth client created"
   - **Click the "DOWNLOAD JSON" button** (or the download icon)
   - This downloads a file like `client_secret_123456.json`

8. Click **"OK"** to close the popup

---

## Step 6: Rename and Move the File

1. Find the file you just downloaded (probably in your Downloads folder)
   - It's named something like `client_secret_1234567890-abc123.apps.googleusercontent.com.json`

2. **Rename it to:** `gdrive_credentials.json`
   - Right-click → Rename
   - Remove the entire old name
   - Type: `gdrive_credentials.json`

3. **Move it to your project folder:**
   - Cut the file (Ctrl+X)
   - Navigate to: `F:\Repos\VideoChunking\`
   - Paste it there (Ctrl+V)

4. **Verify it's in the right place:**
   - You should see `gdrive_credentials.json` next to `app.py` and `README.md`

---

## Step 7: Test It!

1. Start your app: `python app.py`

2. Go to the **"Document Viewer"** tab

3. Click **"🔐 Authorize with Google"**

4. Your browser should open asking you to authorize

5. You'll see a warning that says "Google hasn't verified this app"
   - This is normal! YOU created this app, so it's safe
   - Click **"Advanced"**
   - Click **"Go to D&D Session Processor (unsafe)"**

6. Grant permission to access your Drive

7. Return to the app - you should see "Success!"

---

## Troubleshooting

### "credentials file not found"
- Make sure the file is named **exactly** `gdrive_credentials.json` (lowercase, no spaces)
- Make sure it's in `F:\Repos\VideoChunking\` (the root folder, not in a subfolder)

### "App hasn't been verified"
- This is normal for testing apps
- Click "Advanced" → "Go to [app name] (unsafe)"
- You created it, so it's safe!

### "Access blocked: This app's request is invalid"
- Make sure you added yourself as a test user (Step 4, part 7)
- Make sure the Drive API is enabled (Step 3)

---

## Security Notes

- The `gdrive_credentials.json` file is in `.gitignore` (won't be committed to git)
- Your app only has **read-only** access (can't modify your files)
- You can revoke access anytime at: https://myaccount.google.com/permissions
- Keep the app in "Testing" mode - you don't need to publish it

---

**That's it! Once you have the credentials file, the single-button OAuth will work perfectly.**
