// ============================================================================
// TRANSCRIPTION STATE MANAGEMENT (SVELTE STORE)
// ============================================================================
// This file creates a Svelte store for managing transcription state across
// your application. Think of it like React Context + useState, or Redux, but
// simpler and built into Svelte.
//
// What is a Svelte store?
// - A reactive data container that components can subscribe to
// - When the store updates, all subscribed components automatically re-render
// - Provides a single source of truth for transcription-related state
//
// Why use a store here?
// - Multiple components need access to transcription state (upload form, results, etc.)
// - State needs to persist across component mounts/unmounts
// - Centralized logic for API calls and state updates
//
// Usage in components:
//   import { transcriptionStore } from '$lib/stores/transcription';
//   $: currentJob = $transcriptionStore.currentJob;  // Auto-updates when store changes
//   transcriptionStore.uploadFile(file);  // Call methods to update state

import { writable } from "svelte/store";
import type { TranscriptionJob } from "../../../../shared/types";
import { TranscriptionAPI } from "../api";

// ============================================================================
// STATE INTERFACE
// ============================================================================
// Defines the shape of our transcription state. This is like a TypeScript
// interface in React or a Redux state shape.
//
// - jobs: Array of all transcription jobs (history)
// - currentJob: The currently selected/active job (for displaying results)
// - error: Error message string (null when no error)
interface TranscriptionState {
  jobs: TranscriptionJob[];
  currentJob: TranscriptionJob | null;
  error: string | null;
}

// ============================================================================
// INITIAL STATE
// ============================================================================
// The default state when the app starts or when reset() is called.
// All values start empty/null/false.
const initialState: TranscriptionState = {
  jobs: [],
  currentJob: null,
  error: null,
};

// ============================================================================
// STORE FACTORY FUNCTION
// ============================================================================
// This function creates a custom store by wrapping Svelte's writable store.
// Instead of exposing the raw store methods (set, update), we create a
// custom API with methods specific to transcription operations.
//
// Why a factory function?
// - Encapsulates store logic in one place
// - Provides a clean, domain-specific API
// - Allows us to add custom methods that combine multiple operations
//
// The pattern:
// 1. Create a writable store with initial state
// 2. Get subscribe, set, and update methods from writable
// 3. Return an object with subscribe + custom methods
// 4. Components can use $store syntax or call methods directly
function createTranscriptionStore() {
  // ========================================================================
  // CREATE WRITABLE STORE
  // ========================================================================
  // writable() creates a reactive store. It returns three methods:
  // - subscribe: Components use this to react to state changes
  // - set: Replace the entire state (used in reset())
  // - update: Update state using a function (receives current state, returns new state)
  const { subscribe, set, update } = writable<TranscriptionState>(initialState);

  // ========================================================================
  // RETURN CUSTOM STORE API
  // ========================================================================
  // We return an object that:
  // 1. Exposes subscribe (required for Svelte reactivity)
  // 2. Adds custom methods for transcription operations
  // Components can use: $transcriptionStore.currentJob (auto-subscribes)
  // Or call methods: transcriptionStore.uploadFile(file)
  return {
    subscribe, // Required: allows components to subscribe to state changes

    // ========================================================================
    // UPLOAD FILE
    // ========================================================================
    // Main method for uploading an audio file and starting transcription.
    // This method:
    // 1. Updates state to show upload in progress
    // 2. Calls the API to upload the file (with progress tracking)
    // 3. Adds the job to the jobs array
    // 4. Starts polling for transcription completion
    //
    // Parameters:
    // - file: The audio file to upload (from <input type="file">)
    // - language: Optional language hint (e.g., "en", "es")
    // - onXhrReady: Optional callback that receives XHR object (for cancellation)
    //
    // Returns: The job object with job_id and initial status
    async uploadFile(
      file: File,
      language?: string,
      onXhrReady?: (xhr: XMLHttpRequest) => void
    ) {
      // ====================================================================
      // SET UPLOADING STATE
      // ====================================================================
      // Update state to indicate upload has started. This triggers UI updates
      // (shows progress bar, disables upload button, etc.)
      // The spread operator (...) keeps existing state, only updates specified fields
      update((state) => ({
        ...state,
        error: null, // Clear any previous errors
      }));

      try {
        // ====================================================================
        // UPLOAD FILE TO BACKEND
        // ====================================================================
        // Call the API client to upload the file. The API handles:
        // - Creating FormData
        // - Sending to backend
        const job = await TranscriptionAPI.uploadAudio(
          file,
          language,
          onXhrReady // Pass through XHR reference for cancellation
        );

        // ====================================================================
        // UPLOAD SUCCESS - UPDATE STATE
        // ====================================================================
        // Upload completed successfully. The backend returned a job object.
        // We:
        // 1. Add the job to the jobs array (prepend, so newest is first)
        // 2. Set it as the current job (for displaying results)
        // 3. Reset upload flags
        update((state) => ({
          ...state,
          jobs: [job, ...state.jobs], // Add to front of array (newest first)
          currentJob: job, // Set as active job
        }));

        return job;
      } catch (error) {
        // ====================================================================
        // UPLOAD ERROR - UPDATE STATE
        // ====================================================================
        // Something went wrong (network error, file too large, etc.)
        // Update state to show error and reset upload flags
        const errorMessage =
          error instanceof Error ? error.message : "Upload failed";
        update((state) => ({
          ...state,
          error: errorMessage, // Show error message
        }));
        throw error; // Re-throw so caller can handle it
      }
    },

    // ========================================================================
    // DELETE JOB
    // ========================================================================
    // Removes a transcription job from both the backend and the store.
    // This is called when the user wants to clear a job from their history.
    //
    // Steps:
    // 1. Call API to delete job on backend
    // 2. Remove job from jobs array (using filter)
    // 3. Clear currentJob if it's the one being deleted
    async deleteJob(jobId: string) {
      try {
        // Delete from backend
        await TranscriptionAPI.deleteJob(jobId);

        // Remove from store
        update((state) => ({
          ...state,
          // filter() creates new array without the deleted job
          jobs: state.jobs.filter((j) => j.job_id !== jobId),
          // Clear currentJob if it's the one being deleted
          currentJob:
            state.currentJob?.job_id === jobId ? null : state.currentJob,
        }));
      } catch (error) {
        // If deletion fails, show error but don't crash
        const errorMessage =
          error instanceof Error ? error.message : "Delete failed";
        update((state) => ({ ...state, error: errorMessage }));
      }
    },

    // ========================================================================
    // SET CURRENT JOB
    // ========================================================================
    // Allows components to programmatically select which job to display.
    // This is useful when showing a list of jobs and user clicks one to view.
    //
    // Example: User clicks a job in history -> setCurrentJob(job) -> UI shows that job
    setCurrentJob(job: TranscriptionJob | null) {
      update((state) => ({ ...state, currentJob: job }));
    },

    // ========================================================================
    // UPDATE JOB
    // ========================================================================
    // Updates a job in both the jobs array and currentJob if it matches.
    // Used when checking job status and detecting completion.
    updateJob(job: TranscriptionJob) {
      update((state) => ({
        ...state,
        jobs: state.jobs.map((j) => (j.job_id === job.job_id ? job : j)),
        currentJob:
          state.currentJob?.job_id === job.job_id ? job : state.currentJob,
      }));
    },

    // ========================================================================
    // CANCEL UPLOAD
    // ========================================================================
    // Resets upload-related state. This is called when user cancels an upload
    // (e.g., clicks cancel button). Note: This doesn't actually cancel the
    // XHR request - that should be done via the onXhrReady callback.
    //
    // This just resets the UI state to show upload is no longer in progress.
    cancelUpload() {
      update((state) => ({
        ...state,
        error: null, // Clear any errors
      }));
    },

    // ========================================================================
    // CLEAR ERROR
    // ========================================================================
    // Simple utility to clear error messages from the store.
    // Useful for dismissing error notifications in the UI.
    clearError() {
      update((state) => ({ ...state, error: null }));
    },

    // ========================================================================
    // RESET STORE
    // ========================================================================
    // Resets the entire store to initial state. This is useful for:
    // - Logging out
    // - Starting fresh
    // - Testing/debugging
    //
    // Uses set() instead of update() because we're replacing the entire state.
    reset() {
      set(initialState);
    },
  };
}

// ============================================================================
// EXPORT STORE INSTANCE
// ============================================================================
// Create a single instance of the store and export it.
// This is a singleton pattern - all components import the same store instance,
// so they all share the same state.
//
// Usage in components:
//   import { transcriptionStore } from '$lib/stores/transcription';
//
//   // Auto-subscribe (reactive - updates when store changes)
//   $: currentJob = $transcriptionStore.currentJob;
//
//   // Call methods
//   transcriptionStore.uploadFile(file);
//   transcriptionStore.deleteJob(jobId);
export const transcriptionStore = createTranscriptionStore();
