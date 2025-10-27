# Campaign Chat KeyError Fix

**Date**: 2025-10-26
**Issue**: KeyError: 'session_id' during CampaignChatClient initialization
**Status**: ✅ FIXED

---

## Error Reported

```
ERROR: Error initializing chat client: 'session_id'
Traceback (most recent call last):
  File "F:\Repos\VideoChunking\src\ui\campaign_chat_tab.py", line 45, in initialize_chat_client
    client = CampaignChatClient(retriever=retriever)
  File "F:\Repos\VideoChunking\src\langchain\campaign_chat.py", line 97, in __init__
    self.system_prompt = self._load_system_prompt()
  File "F:\Repos\VideoChunking\src\langchain\campaign_chat.py", line 184, in _load_system_prompt
    return template.format(
KeyError: 'session_id'
```

---

## Root Cause Analysis

### The Problem

The system prompt template file [prompts/campaign_assistant.txt](prompts/campaign_assistant.txt) contains two types of placeholders:

1. **Actual placeholders** (lines 21-23) - meant to be replaced by `template.format()`:
   - `{campaign_name}`
   - `{num_sessions}`
   - `{pc_names}`

2. **Example placeholders** (lines 27-28) - meant to remain as literal text in examples:
   - `{session_id}`, `{timestamp}`, `{speaker}`, `{quote}` (transcript format)
   - `{type}`, `{name}`, `{information}` (knowledge base format)

### Why It Failed

The code in [campaign_chat.py:184](src/langchain/campaign_chat.py#L184) used:

```python
return template.format(
    campaign_name="Unknown",
    num_sessions=0,
    pc_names="Unknown"
)
```

Python's `str.format()` tries to replace **ALL** `{placeholder}` patterns in the string. When it encountered `{session_id}` in the example section, it looked for a `session_id` parameter (which wasn't provided) and raised a `KeyError`.

---

## Solution

### Fix Applied

Escaped the example placeholders in the template by doubling the braces:

**Before** (prompts/campaign_assistant.txt:27-28):
```
- From transcript: "[Session {session_id}, {timestamp}] {speaker}: {quote}"
- From knowledge base: "[{type}: {name}] {information}"
```

**After**:
```
- From transcript: "[Session {{session_id}}, {{timestamp}}] {{speaker}}: {{quote}}"
- From knowledge base: "[{{type}}: {{name}}] {{information}}"
```

### How It Works

In Python's `str.format()`:
- Single braces `{...}` are replacement fields (gets substituted)
- Double braces `{{...}}` escape to literal single braces (not substituted)

After formatting:
```python
template = "Campaign: {campaign_name}, Format: {{session_id}}"
result = template.format(campaign_name="Test")
# Result: "Campaign: Test, Format: {session_id}"
```

---

## Verification

### Test 1: Template Formatting
```python
template = open('prompts/campaign_assistant.txt', 'r').read()
result = template.format(
    campaign_name='Test Campaign',
    num_sessions=5,
    pc_names='Alice, Bob, Charlie'
)
# ✅ No KeyError
```

### Test 2: Citation Format Preserved
After formatting, the citation format section correctly shows:
```
Source Citation Format:
When citing sources, use this format:
- From transcript: "[Session {session_id}, {timestamp}] {speaker}: {quote}"
- From knowledge base: "[{type}: {name}] {information}"
```

### Test 3: CampaignChatClient Initialization
```python
from src.langchain.campaign_chat import CampaignChatClient
client = CampaignChatClient(retriever=retriever)
# ✅ Initialized successfully
# System prompt loaded: 2439 characters
```

### Test 4: App Startup
```bash
python app.py
# ✅ No ERROR messages
# Starting Gradio web UI on http://127.0.0.1:7860
```

---

## Files Changed

- **[prompts/campaign_assistant.txt](prompts/campaign_assistant.txt:27-28)** - Escaped example placeholders

---

## Lessons Learned

### Python `str.format()` Gotcha

When using `.format()` on templates that contain both:
1. Real placeholders (to be substituted)
2. Example placeholders (to remain as literal text)

You must **escape the examples** by doubling the braces: `{{placeholder}}`

### Alternative Solutions Considered

1. **Use `string.Template`** - Requires `$placeholder` syntax, would need template rewrite
2. **Provide all placeholders** - Would need dummy values for examples, confusing
3. **Custom placeholder syntax** - Overkill for this simple case
4. **Double braces** ✅ - Simple, clear, Pythonic

### Prevention

When creating templates with both real and example placeholders:
- Document which placeholders are real vs. examples
- Escape examples immediately when creating template
- Test template formatting during development

---

## Related Issues

This is unrelated to the 10 bugs found and fixed during the Campaign Chat tab UI/UX improvements. This was a separate initialization error in the LangChain integration that prevented the chat client from loading at all.

**Status**: Both issues now fully resolved
- ✅ UI/UX bugs fixed (10 bugs)
- ✅ KeyError fixed (initialization)

Campaign Chat tab is now fully functional!
