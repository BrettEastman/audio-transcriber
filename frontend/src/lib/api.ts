// ============================================================================
// API CLIENT FOR AUDIO TRANSCRIPTION BACKEND
// ============================================================================
// This file contains a TypeScript class that acts as a client for the FastAPI
// backend. It handles all HTTP requests to the transcription API, including:
// - Uploading audio files with progress tracking
// - Polling for transcription status
// - Managing transcription jobs
//
// Think of this as similar to an Axios instance or a custom fetch wrapper
// that provides a clean interface for your frontend components.

import type { TranscriptionJob, ModelInfo } from "../../../shared/types";

// ============================================================================
// API CONFIGURATION
// ============================================================================
// Base URL for the FastAPI backend. In production, this would be your deployed
// backend URL. The backend runs on port 8000 by default.
const API_BASE_URL = "http://localhost:8000";

// ============================================================================
// TRANSCRIPTION API CLASS
// ============================================================================
// This is a static class (all methods are static), meaning you don't need to
// create an instance. You call methods directly: TranscriptionAPI.uploadAudio()
//
// Why static? This is a utility class - it doesn't need to maintain state
// between calls. All methods are self-contained.
export class TranscriptionAPI {
  // ========================================================================
  // BASE REQUEST METHOD
  // ========================================================================
  // This is a private helper method that wraps the native fetch API.
  // It provides:
  // 1. Consistent error handling
  // 2. Automatic JSON parsing
  // 3. Logging for debugging
  //
  // The <T> is a TypeScript generic - it means "this function returns
  // whatever type you specify when calling it". For example:
  // request<TranscriptionJob> returns Promise<TranscriptionJob>
  //
  // This is similar to creating a base axios instance with interceptors.
  private static async request<T>(
    endpoint: string, // API endpoint (e.g., "/transcribe/123")
    options: RequestInit = {} // Fetch options (method, headers, body, etc.)
  ): Promise<T> {
    console.log(`Making request to: ${API_BASE_URL}${endpoint}`);

    try {
      // Make the HTTP request using the native fetch API
      // The spread operator (...) merges the provided options with defaults
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          ...options.headers,
        },
      });

      console.log(`Response status: ${response.status}`);

      // Check if the response was successful (status 200-299)
      // If not, extract the error message and throw
      if (!response.ok) {
        const error = await response.text();
        console.error(`API Error: ${response.status} - ${error}`);
        throw new Error(`API Error: ${response.status} - ${error}`);
      }

      // Parse and return the JSON response
      // TypeScript knows this returns type T because of the generic
      return response.json();
    } catch (error) {
      // Catch network errors (no connection, timeout, etc.)
      console.error(`Network error:`, error);
      throw error; // Re-throw so the caller can handle it
    }
  }

  // ========================================================================
  // UPLOAD AUDIO FILE
  // ========================================================================
  // This method uploads an audio file to the backend for transcription.
  //
  // Why XMLHttpRequest instead of fetch?
  // - The native fetch API doesn't support upload progress tracking
  // - XMLHttpRequest has an "upload" property with progress events
  // - This allows us to show a progress bar to users during upload
  //
  // Parameters:
  // - file: The audio file to upload (from an <input type="file">)
  // - language: Optional language hint (e.g., "en", "es")
  // - onProgress: Callback function that receives upload progress (0-100)
  // - onXhrReady: Callback that receives the XHR object (for cancellation)
  //
  // Returns: A Promise that resolves with the job information (job_id, status)
  static async uploadAudio(
    file: File,
    language?: string,
    onProgress?: (progress: number) => void,
    onXhrReady?: (xhr: XMLHttpRequest) => void
  ): Promise<TranscriptionJob> {
    // ====================================================================
    // PREPARE FORM DATA
    // ====================================================================
    // FormData is used to send multipart/form-data (required for file uploads)
    // This is the same format HTML forms use when you submit a file input
    const formData = new FormData();
    formData.append("file", file); // Append the file with key "file"
    if (language) {
      formData.append("language", language); // Optional language parameter
    }

    // ====================================================================
    // CREATE XMLHTTPREQUEST FOR PROGRESS TRACKING
    // ====================================================================
    // We wrap this in a Promise so we can use async/await syntax
    // The Promise resolves when upload completes, rejects on error
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest(); // Create XHR object

      // ====================================================================
      // PROVIDE XHR REFERENCE FOR CANCELLATION
      // ====================================================================
      // The caller might want to cancel the upload (e.g., user clicks cancel button)
      // We give them the XHR object so they can call xhr.abort()
      // The ?. is optional chaining - only call if the function exists
      onXhrReady?.(xhr);

      // ====================================================================
      // UPLOAD START EVENT
      // ====================================================================
      // Fires when the upload begins. We set progress to 0% to show the
      // progress bar has started.
      xhr.upload.addEventListener("loadstart", () => {
        console.log("Upload started");
        if (onProgress) {
          onProgress(0);
        }
      });

      // ====================================================================
      // UPLOAD PROGRESS EVENT
      // ====================================================================
      // This fires repeatedly during upload, giving us progress updates.
      // event.loaded = bytes uploaded so far
      // event.total = total bytes to upload
      // We calculate percentage and call the onProgress callback to update UI
      xhr.upload.addEventListener("progress", (event) => {
        console.log("Upload progress event:", {
          loaded: event.loaded,
          total: event.total,
          lengthComputable: event.lengthComputable,
        });

        // Only calculate progress if we know the total size
        // Some servers don't send Content-Length, so total might be 0
        if (event.lengthComputable && onProgress) {
          const progress = Math.round((event.loaded / event.total) * 100);
          console.log(`Upload progress: ${progress}%`);
          onProgress(progress); // Update UI with new progress
        } else if (!event.lengthComputable) {
          console.warn("Progress event not computable - total size unknown");
        }
      });

      // ====================================================================
      // UPLOAD COMPLETE EVENT
      // ====================================================================
      // Fires when the upload finishes (regardless of success/failure)
      // We check the status code to determine if it was successful
      xhr.addEventListener("load", () => {
        console.log("XHR load event fired - upload complete");
        console.log("XHR Response:", xhr.status, xhr.responseText);

        // Ensure progress is set to 100% when upload completes
        // This ensures the UI shows 100% even if the last progress event was missed
        if (onProgress) {
          console.log("Setting progress to 100% on load");
          onProgress(100);
        }

        // Check if the request was successful (HTTP 200)
        if (xhr.status === 200) {
          try {
            // Parse the JSON response (backend returns job info)
            const response = JSON.parse(xhr.responseText);
            resolve(response); // Resolve the Promise with the job data
          } catch (e) {
            console.error("JSON Parse Error:", e);
            reject(new Error("Invalid JSON response"));
          }
        } else {
          // Non-200 status means an error occurred
          console.error("HTTP Error:", xhr.status, xhr.responseText);
          reject(
            new Error(`Upload failed: ${xhr.status} - ${xhr.responseText}`)
          );
        }
      });

      // ====================================================================
      // UPLOAD ERROR EVENT
      // ====================================================================
      // Fires if there's a network error (no connection, timeout, etc.)
      // This is different from an HTTP error (like 404) - this is a network failure
      xhr.addEventListener("error", (event) => {
        console.error("XHR Error:", event);
        reject(new Error("Upload failed - Network error"));
      });

      // ====================================================================
      // START THE UPLOAD
      // ====================================================================
      // Open the connection (method, URL) and send the form data
      // This actually starts the upload process
      xhr.open("POST", `${API_BASE_URL}/transcribe`);
      xhr.send(formData);
    });
  }

  // ========================================================================
  // GET TRANSCRIPTION STATUS
  // ========================================================================
  // Polls the backend to get the current status of a transcription job.
  // The job status can be: "queued", "processing", "completed", or "error"
  // If completed, the response includes the transcribed text and segments.
  //
  // This is called repeatedly (polling) until the job is complete.
  // See pollForCompletion() below for automatic polling.
  static async getTranscriptionStatus(
    jobId: string
  ): Promise<TranscriptionJob> {
    return this.request<TranscriptionJob>(`/transcribe/${jobId}`);
  }

  // ========================================================================
  // DELETE JOB
  // ========================================================================
  // Removes a transcription job from the backend's memory.
  // Useful for cleanup after the user has retrieved the results.
  // In production, this might delete the job from a database.
  static async deleteJob(jobId: string): Promise<void> {
    await this.request(`/transcribe/${jobId}`, {
      method: "DELETE", // Specify DELETE HTTP method
    });
  }

  // ========================================================================
  // GET AVAILABLE MODELS
  // ========================================================================
  // Returns information about available Whisper model sizes.
  // This is useful for documentation or if you want to let users choose
  // model size (though the backend is currently configured to use "medium").
  static async getModels(): Promise<ModelInfo> {
    return this.request<ModelInfo>("/models");
  }

  // ========================================================================
  // HEALTH CHECK
  // ========================================================================
  // Checks if the backend is running and if the Whisper model is loaded.
  // Useful for showing connection status in the UI or for monitoring.
  // Returns: { status: "healthy", model_loaded: true/false }
  static async healthCheck(): Promise<{
    status: string;
    model_loaded: boolean;
  }> {
    return this.request("/health");
  }

  // ========================================================================
  // POLL FOR COMPLETION (AUTOMATIC POLLING)
  // ========================================================================
  // This is a convenience method that automatically polls the backend until
  // the transcription job is complete. Instead of manually calling
  // getTranscriptionStatus() in a loop, you can use this method.
  //
  // How it works:
  // 1. Calls getTranscriptionStatus() every intervalMs milliseconds (default 1 second)
  // 2. Calls onUpdate callback each time status is checked (for UI updates)
  // 3. Stops when status is "completed" or "error"
  // 4. Returns the final job data when complete
  //
  // Parameters:
  // - jobId: The job ID returned from uploadAudio()
  // - onUpdate: Optional callback that receives job updates (for progress UI)
  // - intervalMs: How often to check status (default 1000ms = 1 second)
  //
  // Returns: Promise that resolves with the completed job (includes transcribed text)
  //
  // Example usage:
  //   const job = await TranscriptionAPI.pollForCompletion(
  //     jobId,
  //     (job) => console.log(`Status: ${job.status}`),
  //     2000  // Check every 2 seconds
  //   );
  //   console.log("Transcription:", job.text);
  static async pollForCompletion(
    jobId: string,
    onUpdate?: (job: TranscriptionJob) => void,
    intervalMs: number = 1000
  ): Promise<TranscriptionJob> {
    console.log(`Starting to poll for job: ${jobId}`);

    // Wrap in a Promise so we can use async/await
    return new Promise((resolve, reject) => {
      // ====================================================================
      // POLLING FUNCTION
      // ====================================================================
      // This is a recursive function that calls itself until the job is done.
      // It's similar to a while loop, but uses setTimeout for delays.
      const poll = async () => {
        try {
          console.log(`Polling job status for: ${jobId}`);

          // Check the current job status
          const job = await this.getTranscriptionStatus(jobId);
          console.log(`Job status: ${job.status}`, job);

          // Notify the caller of the update (for UI progress indicators)
          onUpdate?.(job);

          // ================================================================
          // CHECK JOB STATUS AND DECIDE WHAT TO DO
          // ================================================================
          if (job.status === "completed") {
            // Success! The transcription is done, return the results
            console.log(`Job completed: ${jobId}`);
            resolve(job);
          } else if (job.status === "error") {
            // The transcription failed, reject the promise with an error
            console.error(`Job failed: ${jobId}`, job.error);
            reject(new Error(job.error || "Transcription failed"));
          } else {
            // Still processing (status is "queued" or "processing")
            // Schedule another check after the interval
            console.log(
              `Job still processing: ${jobId}, polling again in ${intervalMs}ms`
            );
            setTimeout(poll, intervalMs); // Recursive call after delay
          }
        } catch (error) {
          // If the API call itself fails (network error, etc.), stop polling
          console.error(`Polling error for job ${jobId}:`, error);
          reject(error);
        }
      };

      // Start the polling loop
      poll();
    });
  }
}
