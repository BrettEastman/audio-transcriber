<script lang="ts">
  import { onMount } from "svelte";
  import { SUPPORTED_AUDIO_FORMATS } from "../../../../shared/types.js";
  import { transcriptionStore } from "../stores/transcription.js";

  let storeState = $derived($transcriptionStore);
  let isUploading = $derived(storeState.isUploading);
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

  // Handle Tauri file drop events
  onMount(() => {
    console.log("AudioUpload component mounted");

    // Check if we're running in Tauri
    const setupTauriListeners = async () => {
      try {
        console.log("Attempting to import Tauri API...");
        const { listen } = await import("@tauri-apps/api/event");

        console.log(
          "Successfully imported Tauri API, setting up file drop listener"
        );

        // Listen for file drop events
        const unlisten = await listen("tauri://file-drop", (event) => {
          console.log("File drop event received:", event);
          const files = event.payload as string[];
          if (files && files.length > 0) {
            handleTauriFileDrop(files[0]);
          }
        });

        // Listen for file drop hover events
        const unlistenHover = await listen("tauri://file-drop-hover", () => {
          isDragOver = true;
        });

        const unlistenCancelled = await listen(
          "tauri://file-drop-cancelled",
          () => {
            isDragOver = false;
          }
        );

        // Cleanup listeners when component is destroyed
        return () => {
          unlisten();
          unlistenHover();
          unlistenCancelled();
        };
      } catch (error) {
        console.log("Not running in Tauri, using web drag and drop");
        return undefined;
      }
    };

    setupTauriListeners().then((cleanup) => {
      if (cleanup) {
        // Store cleanup function for later use
        return cleanup;
      }
    });
  });

  // Handle file drop from Tauri (file path)
  async function handleTauriFileDrop(filePath: string) {
    console.log("Handling Tauri file drop:", filePath);
    isDragOver = false;

    try {
      // Extract filename from path
      const fileName =
        filePath.split("/").pop() || filePath.split("\\").pop() || "unknown";

      // Check if it's a supported audio file
      if (!isValidAudioFile({ name: fileName } as File)) {
        alert(
          `Unsupported file type. Please use: ${SUPPORTED_AUDIO_FORMATS.join(", ")}`
        );
        return;
      }

      // For now, show a message that drag and drop is detected but ask user to browse
      // This is a temporary solution until we can properly read files in Tauri
      const useFile = confirm(
        `Drag and drop detected: ${fileName}\n\nDue to current limitations, please click "OK" then use the browse button to select this file, or click "Cancel" to ignore.`
      );

      if (useFile) {
        // Trigger the file input dialog
        triggerFileSelect();
      }
    } catch (error) {
      console.error("Error handling Tauri file drop:", error);
      alert(
        "Drag and drop detected, but please use the browse button to select your file."
      );
    }
  }
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
    onclick={isUploading ? undefined : triggerFileSelect}
    role="button"
    tabindex="0"
    onkeydown={(e) => e.key === "Enter" && triggerFileSelect()}
  >
    <div class="drop-content">
      <i
        class="ri-upload-cloud-2-line upload-icon"
        class:uploading={isUploading}
      ></i>
      <h3>{!isUploading ? "Transcribe Audio File" : "Transcribing..."}</h3>

      {#if isUploading}
        <div class="upload-progress">
          <p>Uploading your file...</p>
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
    background: var(--background);
  }

  .drop-zone.drag-over {
    border-color: var(--dashed-border-hover);
    background: var(--background);
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
