export interface TranscriptionJob {
  job_id: string;
  status: "queued" | "processing" | "completed" | "error";
  text?: string;
  segments?: TranscriptionSegment[];
  language?: string;
  error?: string;
  filename?: string;
}

export interface TranscriptionSegment {
  id: number;
  seek: number;
  start: number;
  end: number;
  text: string;
  tokens: number[];
  temperature: number;
  avg_logprob: number;
  compression_ratio: number;
  no_speech_prob: number;
  words?: WordTimestamp[];
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  probability: number;
}

export interface ModelInfo {
  current_model: string;
  available_models: {
    [key: string]: {
      size: string;
      speed: string;
      accuracy: string;
    };
  };
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

// Supported audio formats
export const SUPPORTED_AUDIO_FORMATS = [
  ".mp3",
  ".wav",
  ".m4a",
  ".mp4",
  ".avi",
  ".mov",
  ".flv",
  ".wmv",
  ".aac",
  ".ogg",
] as const;

export type SupportedAudioFormat = (typeof SUPPORTED_AUDIO_FORMATS)[number];
