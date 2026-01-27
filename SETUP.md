# Setup Instructions

## Google Apps Script Setup

The `sheets.py` module requires a Google Apps Script deployed as a web app to interact with Google Sheets.

### Step 1: Create a Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new spreadsheet
3. Name it something like "Kommunal Grundsalg Monitor"
4. The script will automatically create the required sheets (`sources`, `seen_urls`, `events`) when needed

### Step 2: Create the Apps Script

1. In your Google Sheet, go to **Extensions** → **Apps Script**
2. Delete any default code in the editor
3. Copy and paste the contents of `apps-script.gs` into the editor
4. Save the project (give it a name like "Sheets Webapp")

### Step 3: Deploy as Web App

1. Click **Deploy** → **New deployment**
2. Click the gear icon (⚙️) next to "Select type" and choose **Web app**
3. Configure the deployment:
   - **Description**: "Sheets API for Kommunal Grundsalg Monitor"
   - **Execute as**: "Me" (your account)
   - **Who has access**: "Anyone" (this allows your Python script to call it)
4. Click **Deploy**
5. **Authorize access** when prompted:
   - Click "Authorize access"
   - Choose your Google account
   - Click "Advanced" → "Go to [Project Name] (unsafe)" (this is safe - it's your own script)
   - Click "Allow"
6. Copy the **Web App URL** - this is your `SHEETS_WEBAPP_URL`

### Step 4: Add the URL to env.local

Add the Web App URL to your `env.local` file:

```
SHEETS_WEBAPP_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
```

Replace `YOUR_SCRIPT_ID` with the actual ID from your deployment URL.

### Step 5: Test the Setup

You can test the connection by running:

```bash
python monitor.py
```

The script should be able to read from and write to your Google Sheet.

## Notes

- The Apps Script will automatically create sheets (`sources`, `seen_urls`, `events`) if they don't exist
- Make sure the Google Sheet is accessible to the account that runs the Apps Script
- If you update the Apps Script code, you'll need to create a new deployment version
