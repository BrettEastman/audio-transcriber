import type { TranscriptionJob, ModelInfo } from "../../../shared/types";

const API_BASE_URL = "http://localhost:8000";

export class TranscriptionAPI {
  private static async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    console.log(`Making request to: ${API_BASE_URL}${endpoint}`);

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          ...options.headers,
        },
      });

      console.log(`Response status: ${response.status}`);

      if (!response.ok) {
        const error = await response.text();
        console.error(`API Error: ${response.status} - ${error}`);
        throw new Error(`API Error: ${response.status} - ${error}`);
      }

      return response.json();
    } catch (error) {
      console.error(`Network error:`, error);
      throw error;
    }
  }

  static async uploadAudio(
    file: File,
    language?: string,
    onProgress?: (progress: number) => void
  ): Promise<TranscriptionJob> {
    const formData = new FormData();
    formData.append("file", file);
    if (language) {
      formData.append("language", language);
    }

    // Create XMLHttpRequest for progress tracking
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && onProgress) {
          const progress = Math.round((event.loaded / event.total) * 100);
          onProgress(progress);
        }
      });

      xhr.addEventListener("load", () => {
        console.log("XHR Response:", xhr.status, xhr.responseText);
        if (xhr.status === 200) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (e) {
            console.error("JSON Parse Error:", e);
            reject(new Error("Invalid JSON response"));
          }
        } else {
          console.error("HTTP Error:", xhr.status, xhr.responseText);
          reject(
            new Error(`Upload failed: ${xhr.status} - ${xhr.responseText}`)
          );
        }
      });

      xhr.addEventListener("error", (event) => {
        console.error("XHR Error:", event);
        reject(new Error("Upload failed - Network error"));
      });

      xhr.open("POST", `${API_BASE_URL}/transcribe`);
      xhr.send(formData);
    });
  }

  static async getTranscriptionStatus(
    jobId: string
  ): Promise<TranscriptionJob> {
    return this.request<TranscriptionJob>(`/transcribe/${jobId}`);
  }

  static async deleteJob(jobId: string): Promise<void> {
    await this.request(`/transcribe/${jobId}`, {
      method: "DELETE",
    });
  }

  static async getModels(): Promise<ModelInfo> {
    return this.request<ModelInfo>("/models");
  }

  static async healthCheck(): Promise<{
    status: string;
    model_loaded: boolean;
  }> {
    return this.request("/health");
  }

  // Utility function to poll for completion
  static async pollForCompletion(
    jobId: string,
    onUpdate?: (job: TranscriptionJob) => void,
    intervalMs: number = 1000
  ): Promise<TranscriptionJob> {
    console.log(`Starting to poll for job: ${jobId}`);
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          console.log(`Polling job status for: ${jobId}`);
          const job = await this.getTranscriptionStatus(jobId);
          console.log(`Job status: ${job.status}`, job);
          onUpdate?.(job);

          if (job.status === "completed") {
            console.log(`Job completed: ${jobId}`);
            resolve(job);
          } else if (job.status === "error") {
            console.error(`Job failed: ${jobId}`, job.error);
            reject(new Error(job.error || "Transcription failed"));
          } else {
            // Continue polling
            console.log(
              `Job still processing: ${jobId}, polling again in ${intervalMs}ms`
            );
            setTimeout(poll, intervalMs);
          }
        } catch (error) {
          console.error(`Polling error for job ${jobId}:`, error);
          reject(error);
        }
      };

      poll();
    });
  }
}
