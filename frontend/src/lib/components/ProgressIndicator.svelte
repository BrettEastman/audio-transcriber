<script lang="ts">
  import type { TranscriptionJob } from "../../../../shared/types.js";

  interface Props {
    job: TranscriptionJob;
    uploadProgress?: number;
  }

  let { job, uploadProgress = 0 }: Props = $props();

  let progressPercentage = $derived(() => {
    if (job.status === "completed") return 100;
    if (job.status === "processing") return 75;
    if (job.status === "queued") return 25;
    if (uploadProgress > 0) return uploadProgress * 0.2; // Upload is 20% of total
    return 0;
  });

  let statusText = $derived(() => {
    if (uploadProgress > 0 && uploadProgress < 100)
      return `Uploading... ${uploadProgress}%`;
    if (job.status === "queued") return "Queued for processing...";
    if (job.status === "processing") return "Transcribing audio...";
    if (job.status === "completed") return "Transcription complete!";
    if (job.status === "error") return `Error: ${job.error}`;
    return "Preparing...";
  });

  let statusIcon = $derived(() => {
    if (job.status === "completed") return "ri-check-circle-line";
    if (job.status === "error") return "ri-error-warning-line";
    if (job.status === "processing") return "ri-loader-4-line";
    return "ri-upload-cloud-line";
  });
</script>

{#if job}
  <div class="progress-container" class:error={job.status === "error"}>
    <div class="progress-header">
      <div class="file-info">
        <i class={statusIcon} class:spinning={job.status === "processing"}></i>
        <div class="file-details">
          <h4>{job.filename || "Audio File"}</h4>
          <p class="status-text">{statusText}</p>
        </div>
      </div>

      {#if job.language}
        <div class="language-badge">
          {job.language.toUpperCase()}
        </div>
      {/if}
    </div>

    <div class="progress-bar-container">
      <div class="progress-bar">
        <div
          class="progress-fill"
          style="width: {progressPercentage()}%"
          class:error={job.status === "error"}
        ></div>
      </div>
      <div class="progress-percentage">
        {Math.round(progressPercentage())}%
      </div>
    </div>

    {#if job.status === "error"}
      <div class="error-message">
        <i class="ri-error-warning-line"></i>
        <span>{job.error}</span>
      </div>
    {/if}
  </div>
{/if}

<style>
  .progress-container {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .progress-container.error {
    border-color: #fca5a5;
    background: #fef2f2;
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex: 1;
  }

  .file-info i {
    font-size: 1.5rem;
    color: var(--dashed-border-hover);
    flex-shrink: 0;
  }

  .file-info i.ri-check-circle-line {
    color: #10b981;
  }

  .file-info i.ri-error-warning-line {
    color: #ef4444;
  }

  .spinning {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .file-details {
    flex: 1;
    min-width: 0;
  }

  .file-details h4 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #1f2937;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .status-text {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: #6b7280;
  }

  .language-badge {
    background: var(--dashed-border-hover);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.025em;
  }

  .progress-bar-container {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .progress-bar {
    flex: 1;
    height: 8px;
    background: #e5e7eb;
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: var(--dashed-border-hover);
    border-radius: 4px;
    transition: width 0.3s ease;
    background-image: linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.1) 25%,
      transparent 25%,
      transparent 50%,
      rgba(255, 255, 255, 0.1) 50%,
      rgba(255, 255, 255, 0.1) 75%,
      transparent 75%,
      transparent
    );
    background-size: 1rem 1rem;
    animation: progress-shine 2s linear infinite;
  }

  .progress-fill.error {
    background: #ef4444;
  }

  @keyframes progress-shine {
    0% {
      background-position: 0 0;
    }
    100% {
      background-position: 1rem 0;
    }
  }

  .progress-percentage {
    font-size: 0.875rem;
    font-weight: 600;
    color: #374151;
    min-width: 3rem;
    text-align: right;
  }

  .error-message {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
    padding: 0.75rem;
    background: #fee2e2;
    border: 1px solid #fecaca;
    border-radius: 8px;
    color: #dc2626;
    font-size: 0.875rem;
  }

  .error-message i {
    color: #dc2626;
    font-size: 1rem;
  }

  @media (max-width: 640px) {
    .progress-container {
      padding: 1rem;
    }

    .progress-header {
      flex-direction: column;
      gap: 1rem;
    }

    .language-badge {
      align-self: flex-start;
    }
  }
</style>
