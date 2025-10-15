# UI Status - Party Management Tab

## Current Status

The **Party Management** tab IS implemented in `app.py` (lines 269-343).

## How to View the Party Management Tab

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Open your browser** to: http://127.0.0.1:7860

3. **Look for the tabs** at the top of the page. You should see:
   - Process Session
   - **Party Management** ← This is the tab you're looking for
   - Speaker Management
   - Document Viewer
   - Configuration
   - Help

4. **Click on "Party Management"** to access import/export functionality

## What You'll See in Party Management Tab

### Export Section (Left Column)
- Dropdown to select which party to export
- "Export Party" button
- Download file output
- Status message

### Import Section (Right Column)
- File upload for party JSON
- Optional Party ID override field
- "Import Party" button
- Status message

## Testing the UI

If you don't see the Party Management tab, try:

1. **Restart the app**:
   ```bash
   # Stop the current app (Ctrl+C)
   python app.py
   ```

2. **Clear browser cache** and refresh the page

3. **Test with the minimal UI**:
   ```bash
   python test_ui.py
   # Opens on port 7861
   ```

4. **Check for errors** in the terminal where you ran `python app.py`

## Verifying the Code

The Party Management tab code exists in `app.py`:

```python
with gr.Tab("Party Management"):  # Line 269
    gr.Markdown("""
    ### Import/Export Party Configurations

    Save your party configurations to share them or keep backups.
    """)

    with gr.Row():
        with gr.Column():
            gr.Markdown("#### Export Party")
            export_party_dropdown = gr.Dropdown(
                choices=available_parties,
                label="Select Party to Export",
                value="default"
            )
            # ... export functionality ...

        with gr.Column():
            gr.Markdown("#### Import Party")
            import_file = gr.File(
                label="Upload Party JSON File",
                file_types=[".json"]
            )
            # ... import functionality ...
```

## Alternative: Use CLI for Import/Export

If you prefer not to use the web UI, the CLI has full import/export functionality:

```bash
# Export a party
python cli.py export-party default my_party.json

# Import a party
python cli.py import-party my_party.json

# Import with custom ID
python cli.py import-party my_party.json --party-id campaign2

# Export all parties
python cli.py export-all-parties backup.json

# List all parties
python cli.py list-parties

# View party details
python cli.py show-party default
```

## Screenshots (What You Should See)

When you click on the **Party Management** tab, you should see:

```
┌─────────────────────────────────────────────────────────┐
│  Import/Export Party Configurations                     │
│  Save your party configurations to share them or keep   │
│  backups.                                               │
├──────────────────────┬──────────────────────────────────┤
│ Export Party         │  Import Party                    │
│                      │                                  │
│ Select Party: ▼      │  Upload Party JSON File          │
│  [default ▼]         │  [Choose File]                   │
│                      │                                  │
│  [Export Party]      │  Party ID (optional)             │
│                      │  [________________]              │
│  Download:           │                                  │
│  [            ]      │  [Import Party]                  │
│                      │                                  │
│  Status:             │  Status:                         │
│  [            ]      │  [            ]                  │
└──────────────────────┴──────────────────────────────────┘
```

## Common Issues

### "I don't see the Party Management tab"

**Possible causes:**
1. App is showing cached version - Hard refresh browser (Ctrl+Shift+R)
2. App didn't restart after code changes - Restart `python app.py`
3. Browser window is too narrow - Tabs might be collapsed
4. JavaScript error - Check browser console (F12)

### "Export/Import doesn't work"

**Check:**
1. `models/` directory exists
2. `models/parties.json` file exists (created automatically on first run)
3. No Python errors in the terminal
4. File permissions allow reading/writing in `models/` directory

## File Locations

- **Party configurations**: `models/parties.json` (auto-created)
- **Example template**: `models/parties.json.example`
- **App code**: `app.py` (lines 269-343 for Party Management tab)
- **Party manager**: `src/party_config.py`

## Next Steps

If the tab still doesn't appear after trying the above:

1. Check the terminal output when running `python app.py` for any errors
2. Run the test UI: `python test_ui.py` to isolate the issue
3. Verify Gradio version: `pip show gradio` (should be recent)
4. Check if there are any Python syntax errors in `app.py`

---

**Last Updated**: Based on current `app.py` code structure
