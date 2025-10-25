# Troubleshooting Guide

This guide provides solutions to common problems you might encounter while using the D&D Session Processor.

---

## Common Errors

### Error: "Audio chunking resulted in zero segments..."

**Problem:**
The processing pipeline fails with a `RuntimeError` and the message "Audio chunking resulted in zero segments. This can happen if the audio is completely silent, corrupt, or too short. Please check the input audio file."

**Cause:**
This error occurs when the audio chunking stage of the pipeline is unable to find any speech in the input audio file. This can be due to several reasons:

*   **The audio file is completely silent:** The VAD (Voice Activity Detection) system will not create any chunks if it doesn't detect any speech.
*   **The audio file is corrupt:** A corrupt audio file may not be readable by the audio processing library, resulting in no audio data being passed to the chunker.
*   **The audio file is too short:** If the audio file is very short (e.g., less than a few seconds), it may not contain enough speech for the chunker to create any segments.

**Solution:**

1.  **Check your audio file:** Make sure that the audio file you are trying to process is not silent, corrupt, or too short. You can try playing the file in a media player to verify its contents.
2.  **Check your audio input:** If you are recording your own audio, make sure that your microphone is working correctly and that you are speaking clearly.
3.  **Adjust VAD settings (Advanced):** If you are sure that your audio file is valid, you can try adjusting the VAD settings in the `src/chunker.py` file. However, this is an advanced option and should only be attempted if you are comfortable with the codebase.
