<script lang="ts">
  import { onMount } from "svelte";
  import { SUPPORTED_AUDIO_FORMATS } from "../../../../shared/types.js";
  import { transcriptionStore } from "../stores/transcription.js";

  let storeState = $derived($transcriptionStore);
  let isUploading = $derived(storeState.isUploading);
  let currentJob = $derived(storeState.currentJob);
  let isTranscribing = $derived(
    currentJob?.status === "queued" || currentJob?.status === "processing"
  );
  let transcriptionProgress = $state(0);
  let transcriptionStartTime = $state<number | null>(null);
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

    console.log(
      "Uploading file:",
      file.name,
      "Size:",
      file.size,
      "Type:",
      file.type
    );

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
        return;
      }

      console.error("Upload failed:", error);
      alert(
        `Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`
      );
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
    transcriptionStore.cancelUpload();
  }

  // Track transcription progress - calculate based on segments when available
  $effect(() => {
    if (isTranscribing && !transcriptionStartTime) {
      // Transcription just started
      transcriptionStartTime = Date.now();
      transcriptionProgress = 10; // Start at 10%
    } else if (!isTranscribing && transcriptionStartTime) {
      // Transcription completed or not started
      transcriptionStartTime = null;
      if (currentJob?.status === "completed") {
        transcriptionProgress = 100;
      } else {
        transcriptionProgress = 0;
      }
    } else if (currentJob?.status === "completed") {
      // Ensure progress shows 100% when completed
      transcriptionProgress = 100;
    }
  });

  // Update transcription progress - smooth time-based estimation
  onMount(() => {
    const interval = setInterval(() => {
      if (isTranscribing && transcriptionStartTime) {
        const elapsed = Date.now() - transcriptionStartTime;
        const elapsedSeconds = elapsed / 1000;

        // Smooth progress curve: starts fast, slows down as it approaches completion
        // This gives a more realistic feel than linear progress
        // Formula: 10% + (90% * smooth curve that approaches but never reaches 100%)
        const smoothProgress = 1 - Math.exp(-elapsedSeconds / 30); // Exponential approach
        const progress = Math.min(
          95, // Cap at 95% until actually complete
          10 + smoothProgress * 85
        );
        transcriptionProgress = Math.round(progress);
      }
    }, 500); // Update every 500ms for smoother animation

    return () => clearInterval(interval);
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
    onclick={isUploading || isTranscribing ? undefined : triggerFileSelect}
    role="button"
    tabindex="0"
    onkeydown={(e) => e.key === "Enter" && triggerFileSelect()}
  >
    <div class="drop-content">
      <i
        class="ri-upload-cloud-2-line upload-icon"
        class:uploading={isUploading || isTranscribing}
      ></i>
      <h3>
        {#if isTranscribing}
          Transcribing...
        {:else}
          Transcribe Audio File
        {/if}
      </h3>

      {#if isUploading}
        <div class="upload-progress">
          <p>Uploading file...</p>
          <button class="cancel-btn" onclick={(e) => cancelUpload(e)}>
            <i class="ri-close-line"></i>
            Cancel
          </button>
        </div>
      {:else if isTranscribing}
        <div class="upload-progress">
          <p>Transcribing audio... {transcriptionProgress}%</p>
          <div class="progress-bar-container">
            <div
              class="progress-bar"
              style="width: {transcriptionProgress}%"
            ></div>
          </div>
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
