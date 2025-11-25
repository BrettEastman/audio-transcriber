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
  // - onXhrReady: Callback that receives the XHR object (for cancellation)
  //
  // Returns: A Promise that resolves with the job information (job_id, status)
  static async uploadAudio(
    file: File,
    language?: string,
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
      // UPLOAD COMPLETE EVENT
      // ====================================================================
      // Fires when the upload finishes (regardless of success/failure)
      // We check the status code to determine if it was successful
      xhr.addEventListener("load", () => {
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
  // GET TRANSCRIPTION STATUS (SIMPLE CHECK)
  // ========================================================================
  // Checks the current status of a transcription job.
  // Used for simple completion checks, not continuous polling.
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
}
