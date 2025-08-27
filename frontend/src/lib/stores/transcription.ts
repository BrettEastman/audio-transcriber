import { writable } from "svelte/store";
import type { TranscriptionJob } from "../../../../shared/types";
import { TranscriptionAPI } from "../api";

interface TranscriptionState {
  jobs: TranscriptionJob[];
  currentJob: TranscriptionJob | null;
  uploadProgress: number;
  isUploading: boolean;
  error: string | null;
}

const initialState: TranscriptionState = {
  jobs: [],
  currentJob: null,
  uploadProgress: 0,
  isUploading: false,
  error: null,
};

function createTranscriptionStore() {
  const { subscribe, set, update } = writable<TranscriptionState>(initialState);

  return {
    subscribe,

    async uploadFile(file: File, language?: string) {
      update((state) => ({
        ...state,
        isUploading: true,
        uploadProgress: 0,
        error: null,
      }));

      try {
        const job = await TranscriptionAPI.uploadAudio(
          file,
          language,
          (progress) => {
            update((state) => ({ ...state, uploadProgress: progress }));
          }
        );

        update((state) => ({
          ...state,
          jobs: [job, ...state.jobs],
          currentJob: job,
          isUploading: false,
          uploadProgress: 0,
        }));

        // Start polling for completion
        this.pollJob(job.job_id);

        return job;
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Upload failed";
        update((state) => ({
          ...state,
          isUploading: false,
          uploadProgress: 0,
          error: errorMessage,
        }));
        throw error;
      }
    },

    async pollJob(jobId: string) {
      try {
        const completedJob = await TranscriptionAPI.pollForCompletion(
          jobId,
          (job) => {
            update((state) => ({
              ...state,
              jobs: state.jobs.map((j) => (j.job_id === jobId ? job : j)),
              currentJob:
                state.currentJob?.job_id === jobId ? job : state.currentJob,
            }));
          }
        );

        update((state) => ({
          ...state,
          jobs: state.jobs.map((j) => (j.job_id === jobId ? completedJob : j)),
          currentJob:
            state.currentJob?.job_id === jobId
              ? completedJob
              : state.currentJob,
        }));
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Transcription failed";
        update((state) => ({
          ...state,
          error: errorMessage,
          jobs: state.jobs.map((j) =>
            j.job_id === jobId
              ? { ...j, status: "error" as const, error: errorMessage }
              : j
          ),
        }));
      }
    },

    async deleteJob(jobId: string) {
      try {
        await TranscriptionAPI.deleteJob(jobId);
        update((state) => ({
          ...state,
          jobs: state.jobs.filter((j) => j.job_id !== jobId),
          currentJob:
            state.currentJob?.job_id === jobId ? null : state.currentJob,
        }));
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Delete failed";
        update((state) => ({ ...state, error: errorMessage }));
      }
    },

    setCurrentJob(job: TranscriptionJob | null) {
      update((state) => ({ ...state, currentJob: job }));
    },

    clearError() {
      update((state) => ({ ...state, error: null }));
    },

    reset() {
      set(initialState);
    },
  };
}

export const transcriptionStore = createTranscriptionStore();
