<script lang="ts">
  import { onMount } from "svelte";
  import { SUPPORTED_AUDIO_FORMATS } from "../../../../shared/types.js";
  import { transcriptionStore } from "../stores/transcription.js";
  import { TranscriptionAPI } from "../api.js";

  let storeState = $derived($transcriptionStore);
  let currentJob = $derived(storeState.currentJob);
  let isTranscribing = $derived(
    currentJob &&
      (currentJob.status === "queued" ||
        currentJob.status === "processing" ||
        !currentJob.text)
  );
  let fakeProgress = $state(0);
  let fakeProgressInterval: ReturnType<typeof setInterval> | null = null;
  let isShowingProgress = $state(false);
  let isDragOver = $state(false);
  let fileInput: HTMLInputElement;
  let selectedLanguage = $state<string>("");
  let currentXhr: XMLHttpRequest | null = null;

  const languages = [
    { code: "", name: "Auto-detect" },
    { code: "en", name: "English" },
    { code: "es", name: "Spanish" },
    { code: "fr", name: "French" },
    { code: "de", name: "German" },
    { code: "it", name: "Italian" },
    { code: "pt", name: "Portuguese" },
    { code: "ja", name: "Japanese" },
    { code: "ko", name: "Korean" },
    { code: "zh", name: "Chinese" },
  ];

  function isValidAudioFile(file: File): boolean {
    const extension = "." + file.name.split(".").pop()?.toLowerCase();
    return SUPPORTED_AUDIO_FORMATS.includes(extension as any);
  }

  async function handleFileUpload(file: File) {
    if (!isValidAudioFile(file)) {
      alert(
        `Unsupported file type. Please use: ${SUPPORTED_AUDIO_FORMATS.join(", ")}`
      );
      return;
    }

    // Start fake progress bar immediately when file is selected
    if (fakeProgressInterval) {
      clearInterval(fakeProgressInterval);
    }
    fakeProgress = 0;
    isShowingProgress = true; // Show progress bar immediately
    fakeProgressInterval = setInterval(() => {
      if (fakeProgress < 95) {
        const increment = 2 + Math.random() * 3;
        fakeProgress = Math.min(95, fakeProgress + increment);
      }
    }, 250);

    try {
      await transcriptionStore.uploadFile(
        file,
        selectedLanguage || undefined,
        (xhr) => {
          currentXhr = xhr;
        }
      );
    } catch (error) {
      // Check if it was cancelled
      if (error instanceof Error && error.message.includes("abort")) {
        console.log("Upload cancelled by user");
        // Stop progress bar on cancel
        if (fakeProgressInterval) {
          clearInterval(fakeProgressInterval);
          fakeProgressInterval = null;
        }
        fakeProgress = 0;
        isShowingProgress = false;
        return;
      }

      console.error("Upload failed:", error);
      alert(
        `Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`
      );
      // Stop progress bar on error
      if (fakeProgressInterval) {
        clearInterval(fakeProgressInterval);
        fakeProgressInterval = null;
      }
      fakeProgress = 0;
      isShowingProgress = false;
    } finally {
      currentXhr = null;
    }
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    isDragOver = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    isDragOver = true;
  }

  function handleDragLeave(event: DragEvent) {
    event.preventDefault();
    isDragOver = false;
  }

  function handleFileSelect(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  }

  function triggerFileSelect() {
    fileInput.click();
  }

  function cancelUpload(event: Event) {
    event.stopPropagation(); // Prevent triggering the drop zone click
    if (currentXhr) {
      currentXhr.abort();
      currentXhr = null;
    }
    // Stop progress bar
    if (fakeProgressInterval) {
      clearInterval(fakeProgressInterval);
      fakeProgressInterval = null;
    }
    fakeProgress = 0;
    isShowingProgress = false;
    transcriptionStore.cancelUpload();
  }

  // Stop progress bar when transcription completes
  $effect(() => {
    if (currentJob?.status === "completed" && fakeProgressInterval) {
      clearInterval(fakeProgressInterval);
      fakeProgressInterval = null;
      fakeProgress = 0;
      isShowingProgress = false; // Hide progress bar when done
    }
  });

  // Simple completion check - check job status periodically (every 3 seconds)
  let completionCheckInterval: ReturnType<typeof setInterval> | null = null;

  $effect(() => {
    // Start checking for completion when we have a job that's transcribing
    if (isTranscribing && !completionCheckInterval) {
      completionCheckInterval = setInterval(async () => {
        if (!currentJob || !isTranscribing) {
          if (completionCheckInterval) {
            clearInterval(completionCheckInterval);
            completionCheckInterval = null;
          }
          return;
        }

        try {
          const job = await TranscriptionAPI.getTranscriptionStatus(
            currentJob.job_id
          );
          if (job.status === "completed" || job.status === "error") {
            if (completionCheckInterval) {
              clearInterval(completionCheckInterval);
              completionCheckInterval = null;
            }
            // Update the store with the completed job
            transcriptionStore.updateJob(job);
          }
        } catch (error) {
          console.error("Error checking job status:", error);
        }
      }, 3000); // Check every 3 seconds
    }

    // Stop checking if job completes or is no longer transcribing
    if (!isTranscribing && completionCheckInterval) {
      clearInterval(completionCheckInterval);
      completionCheckInterval = null;
    }
  });

  // Cleanup intervals on unmount
  onMount(() => {
    return () => {
      if (fakeProgressInterval) {
        clearInterval(fakeProgressInterval);
      }
      if (completionCheckInterval) {
        clearInterval(completionCheckInterval);
      }
    };
  });
</script>

<div class="upload-container">
  <div class="language-selector">
    <label for="language">Language:</label>
    <select bind:value={selectedLanguage} id="language">
      {#each languages as lang}
        <option value={lang.code}>{lang.name}</option>
      {/each}
    </select>
  </div>

  <div
    class="drop-zone"
    class:drag-over={isDragOver}
    ondrop={handleDrop}
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    onclick={isShowingProgress ? undefined : triggerFileSelect}
    role="button"
    tabindex="0"
    onkeydown={(e) => e.key === "Enter" && triggerFileSelect()}
  >
    <div class="drop-content">
      <i
        class="ri-upload-cloud-2-line upload-icon"
        class:uploading={isShowingProgress}
      ></i>
      <h3>
        {#if isShowingProgress}
          Transcribing...
        {:else}
          Transcribe Audio File
        {/if}
      </h3>

      {#if isShowingProgress}
        <div class="upload-progress">
          <p>Transcribing audio... {Math.round(fakeProgress)}%</p>
          <div class="progress-bar-container">
            <div class="progress-bar" style="width: {fakeProgress}%"></div>
          </div>
          <button class="cancel-btn" onclick={(e) => cancelUpload(e)}>
            <i class="ri-close-line"></i>
            Cancel
          </button>
        </div>
      {:else}
        <p>Drag and drop your audio file here, or click to browse</p>
        <div class="supported-formats">
          <small>Supports: MP3, WAV, M4A, MP4, and more</small>
        </div>
      {/if}
    </div>
  </div>

  <input
    bind:this={fileInput}
    type="file"
    accept={SUPPORTED_AUDIO_FORMATS.join(",")}
    onchange={handleFileSelect}
    style="display: none;"
  />
</div>

<style>
  .upload-container {
    width: 100%;
    max-width: 600px;
    margin: 0 auto;
  }

  .language-selector {
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .language-selector label {
    font-weight: 500;
    color: var(--blue-dark);
  }

  .language-selector select {
    padding: 0.5rem;
    border: 2px solid var(--dashed-border);
    border-radius: 8px;
    background: var(--white-background);
    font-size: 0.875rem;
    cursor: pointer;
  }

  .language-selector select:focus {
    outline: none;
    border-color: var(--dashed-border-hover);
  }

  .drop-zone {
    border: 3px dashed var(--dashed-border);
    border-radius: 12px;
    padding: 3rem 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    background: var(--white-background);
  }

  .drop-zone:has(.upload-progress) {
    cursor: default;
  }

  .drop-zone:hover {
    border-color: var(--dashed-border-hover);
    background: var(--white-bg-darker);
  }

  .drop-zone.drag-over {
    border-color: var(--dashed-border-hover);
    background: var(--white-bg-darker);
    transform: scale(1.02);
  }

  .drop-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .upload-icon {
    font-size: 3rem;
    color: var(--upload-icon);
    transition: color 0.3s ease;
  }

  .drop-zone:hover .upload-icon,
  .drop-zone.drag-over .upload-icon {
    color: var(--dashed-border-hover);
  }

  .upload-icon.uploading {
    color: var(--dashed-border-hover);
    animation: pulse 1.5s linear infinite;
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
      color: var(--dashed-border);
    }
    50% {
      transform: scale(1.05);
      color: var(--pulse-dark);
    }
    100% {
      transform: scale(1);
      color: var(--dashed-border);
    }
  }

  .drop-content h3 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--blue-dark);
  }

  .drop-content p {
    margin: 0;
    color: var(--upload-icon);
    font-size: 1rem;
  }

  .supported-formats {
    margin-top: 0.5rem;
  }

  .supported-formats small {
    color: var(--upload-icon);
    font-size: 0.75rem;
  }

  .upload-progress {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    width: 100%;
  }

  .progress-bar-container {
    width: 100%;
    max-width: 400px;
    height: 8px;
    background: var(--dashed-border);
    border-radius: 4px;
    overflow: hidden;
    position: relative;
  }

  .progress-bar {
    height: 100%;
    background: linear-gradient(
      90deg,
      var(--dashed-border-hover),
      var(--pulse-dark)
    );
    border-radius: 4px;
    transition: width 0.3s ease;
    position: relative;
    overflow: hidden;
  }

  .progress-bar::after {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(255, 255, 255, 0.3),
      transparent
    );
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(100%);
    }
  }

  .cancel-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--warning-background);
    color: var(--blue-dark);
    border: none;
    border-radius: 6px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .cancel-btn:hover {
    background: var(--warning-light);
  }

  .cancel-btn:active {
    transform: translateY(1px);
  }

  @media (max-width: 640px) {
    .drop-zone {
      padding: 2rem 1rem;
    }

    .upload-icon {
      font-size: 2.5rem;
    }

    .drop-content h3 {
      font-size: 1.25rem;
    }
  }
</style>
