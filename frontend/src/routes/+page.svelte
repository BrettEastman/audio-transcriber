<script lang="ts">
  import AudioUpload from "$lib/components/AudioUpload.svelte";
  import TranscriptionResult from "$lib/components/TranscriptionResult.svelte";
  import { transcriptionStore } from "$lib/stores/transcription";
  import { onMount } from "svelte";

  let storeState = $derived($transcriptionStore);
  let jobs = $derived(storeState.jobs);
  let currentJob = $derived(storeState.currentJob);
  let error = $derived(storeState.error);

  let isBackendReady = $state(false);
  let isCheckingBackend = $state(true);

  async function checkBackendHealth() {
    try {
      const response = await fetch("http://localhost:8000/health");
      if (response.ok) {
        const data = await response.json();
        return data.model_loaded;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  // Poll backend until it's ready
  async function waitForBackend() {
    isCheckingBackend = true;
    let attempts = 0;
    const maxAttempts = 30; // 30 seconds timeout

    while (attempts < maxAttempts) {
      const ready = await checkBackendHealth();
      if (ready) {
        isBackendReady = true;
        isCheckingBackend = false;
        return;
      }

      attempts++;
      await new Promise((resolve) => setTimeout(resolve, 1000)); // Wait 1 second
    }

    isCheckingBackend = false;
    // Backend didn't start - could show an error message
  }

  onMount(() => {
    waitForBackend();
  });

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
    {#if isCheckingBackend}
      <div class="loading-screen">
        <div class="loading-content">
          <h2>Starting Audio Transcriber</h2>
          <p>Loading Whisper AI model... This may take a moment.</p>
        </div>
      </div>
    {:else if !isBackendReady}
      <div class="error-screen">
        <div class="error-content">
          <i class="ri-error-warning-line"></i>
          <h2>Backend Not Available</h2>
          <p>Please make sure the backend server is running.</p>
          <button onclick={() => waitForBackend()} class="retry-btn">
            <i class="ri-refresh-line"></i>
            Retry
          </button>
        </div>
      </div>
    {:else}
      {#if error}
        <div class="error-banner">
          <i class="ri-error-warning-line"></i>
          <span>{error}</span>
          <button
            aria-label="Close"
            onclick={() => transcriptionStore.clearError()}
          >
            <i class="ri-close-line"></i>
          </button>
        </div>
      {/if}

      <div class="main-content">
        <section class="upload-section">
          <AudioUpload />
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
                      <span class="status status-{job.status}"
                        >{job.status}</span
                      >
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
                      aria-label="Delete"
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
    {/if}
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background: var(--white-background);
  }

  .app {
    min-height: 100vh;
  }

  .app-header {
    background: var(--white-bg-darker);
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
    background: var(--warning-background);
    border: 1px solid var(--warning-lighter);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: var(--warning);
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
    color: var(--warning);
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 4px;
  }

  .error-banner button:hover {
    background: var(--warning-mid);
  }

  .main-content {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .upload-section {
    background: var(--white-background);
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }

  .result-section,
  .history-section {
    background: var(--white-background);
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }

  .result-section h2,
  .history-section h2 {
    margin: 0 0 1.5rem 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--blue-dark);
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
    border: 1px solid var(--border-darker);
    border-radius: 8px;
    background: var(--white-background);
  }

  .job-info {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex: 1;
  }

  .job-info i {
    font-size: 1.25rem;
    color: var(--upload-icon);
  }

  .job-info h4 {
    margin: 0;
    font-size: 1rem;
    font-weight: 500;
    color: var(--blue-dark);
  }

  .status {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-weight: 500;
    text-transform: uppercase;
  }

  .status-completed {
    background: var(--status-completed-bg);
    color: var(--status-completed);
  }

  .status-processing {
    background: var(--status-processing-bg);
    color: var(--status-processing);
  }

  .status-queued {
    background: var(--status-queued-bg);
    color: var(--status-queued);
  }

  .status-error {
    background: var(--warning-background);
    color: var(--warning);
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
    background: var(--dashed-border-hover);
    color: var(--white-background);
  }

  .view-btn:hover {
    background: var(--dashed-border-hover);
  }

  .delete-btn {
    background: var(--white-background);
    color: var(--upload-icon);
  }

  .delete-btn:hover {
    background: var(--warning-background);
    color: var(--warning);
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

    .loading-content,
    .error-content {
      padding: 1rem;
    }
  }
</style>
