<script lang="ts">
  import AudioUpload from "$lib/components/AudioUpload.svelte";
  import ProgressIndicator from "$lib/components/ProgressIndicator.svelte";
  import TranscriptionResult from "$lib/components/TranscriptionResult.svelte";
  import { transcriptionStore } from "$lib/stores/transcription";

  // Subscribe to store values
  $: ({ jobs, currentJob, isUploading, uploadProgress, error } =
    $transcriptionStore);

  function handleJobDelete(jobId: string) {
    transcriptionStore.deleteJob(jobId);
  }
</script>

<svelte:head>
  <title>Audio Transcriber</title>
  <meta
    name="description"
    content="Local audio transcription with Whisper AI"
  />
</svelte:head>

<main class="app">
  <header class="app-header">
    <div class="header-content">
      <h1>
        <i class="ri-mic-line"></i>
        Audio Transcriber
      </h1>
      <p>Local transcription powered by OpenAI Whisper</p>
    </div>
  </header>

  <div class="container">
    {#if error}
      <div class="error-banner">
        <i class="ri-error-warning-line"></i>
        <span>{error}</span>
        <button onclick={() => transcriptionStore.clearError()}>
          <i class="ri-close-line"></i>
        </button>
      </div>
    {/if}

    <div class="main-content">
      <section class="upload-section">
        <AudioUpload />

        {#if isUploading || (currentJob && currentJob.status !== "completed")}
          {#if currentJob}
            <ProgressIndicator job={currentJob} {uploadProgress} />
          {/if}
        {/if}
      </section>

      {#if currentJob && currentJob.status === "completed"}
        <section class="result-section">
          <h2>Latest Transcription</h2>
          <TranscriptionResult
            job={currentJob}
            onDelete={() => handleJobDelete(currentJob.job_id)}
          />
        </section>
      {/if}

      {#if jobs.length > 1}
        <section class="history-section">
          <h2>Recent Transcriptions</h2>
          <div class="job-list">
            {#each jobs.slice(1) as job (job.job_id)}
              <div class="job-item">
                <div class="job-info">
                  <i class="ri-file-text-line"></i>
                  <div>
                    <h4>{job.filename || "Audio File"}</h4>
                    <span class="status status-{job.status}">{job.status}</span>
                  </div>
                </div>

                <div class="job-actions">
                  {#if job.status === "completed"}
                    <button
                      class="view-btn"
                      onclick={() => transcriptionStore.setCurrentJob(job)}
                    >
                      <i class="ri-eye-line"></i>
                      View
                    </button>
                  {/if}

                  <button
                    class="delete-btn"
                    onclick={() => handleJobDelete(job.job_id)}
                  >
                    <i class="ri-delete-bin-line"></i>
                  </button>
                </div>
              </div>
            {/each}
          </div>
        </section>
      {/if}
    </div>
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      sans-serif;
    background: #f8fafc;
    color: #1e293b;
  }

  .app {
    min-height: 100vh;
  }

  .app-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem 0;
    text-align: center;
  }

  .header-content h1 {
    margin: 0 0 0.5rem 0;
    font-size: 2.5rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
  }

  .header-content i {
    font-size: 2.5rem;
  }

  .header-content p {
    margin: 0;
    font-size: 1.125rem;
    opacity: 0.9;
  }

  .container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem 1rem;
  }

  .error-banner {
    background: #fee2e2;
    border: 1px solid #fecaca;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: #dc2626;
  }

  .error-banner i {
    font-size: 1.25rem;
  }

  .error-banner span {
    flex: 1;
  }

  .error-banner button {
    background: none;
    border: none;
    color: #dc2626;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 4px;
  }

  .error-banner button:hover {
    background: rgba(220, 38, 38, 0.1);
  }

  .main-content {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .upload-section {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }

  .result-section,
  .history-section {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }

  .result-section h2,
  .history-section h2 {
    margin: 0 0 1.5rem 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #1f2937;
  }

  .job-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .job-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #fafafa;
  }

  .job-info {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex: 1;
  }

  .job-info i {
    font-size: 1.25rem;
    color: #6b7280;
  }

  .job-info h4 {
    margin: 0;
    font-size: 1rem;
    font-weight: 500;
    color: #1f2937;
  }

  .status {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-weight: 500;
    text-transform: uppercase;
  }

  .status-completed {
    background: #d1fae5;
    color: #065f46;
  }

  .status-processing {
    background: #dbeafe;
    color: #1e40af;
  }

  .status-queued {
    background: #fef3c7;
    color: #92400e;
  }

  .status-error {
    background: #fee2e2;
    color: #dc2626;
  }

  .job-actions {
    display: flex;
    gap: 0.5rem;
  }

  .view-btn,
  .delete-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s ease;
  }

  .view-btn {
    background: #3b82f6;
    color: white;
  }

  .view-btn:hover {
    background: #2563eb;
  }

  .delete-btn {
    background: #f3f4f6;
    color: #6b7280;
  }

  .delete-btn:hover {
    background: #fee2e2;
    color: #dc2626;
  }

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
    }

    .upload-section,
    .result-section,
    .history-section {
      padding: 1.5rem;
    }

    .header-content h1 {
      font-size: 2rem;
    }

    .job-item {
      flex-direction: column;
      align-items: flex-start;
      gap: 1rem;
    }

    .job-actions {
      align-self: flex-end;
    }
  }
</style>
