import type { TranscriptionJob, ModelInfo } from "../../../shared/types";

const API_BASE_URL = "http://localhost:8000";

export class TranscriptionAPI {
  private static async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error: ${response.status} - ${error}`);
    }

    return response.json();
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
        if (xhr.status === 200) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (e) {
            reject(new Error("Invalid JSON response"));
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      });

      xhr.addEventListener("error", () => {
        reject(new Error("Upload failed"));
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
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const job = await this.getTranscriptionStatus(jobId);
          onUpdate?.(job);

          if (job.status === "completed") {
            resolve(job);
          } else if (job.status === "error") {
            reject(new Error(job.error || "Transcription failed"));
          } else {
            // Continue polling
            setTimeout(poll, intervalMs);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }
}
