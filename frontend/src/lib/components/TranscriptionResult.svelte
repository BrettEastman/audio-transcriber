<script lang="ts">
  import type { TranscriptionJob } from "../../../../shared/types.js";

  interface Props {
    job: TranscriptionJob;
    onDelete?: () => void;
  }

  let { job, onDelete }: Props = $props();

  let showSegments = $state(false);
  let copied = $state(false);

  function copyToClipboard() {
    if (job.text) {
      navigator.clipboard.writeText(job.text);
      copied = true;
      setTimeout(() => (copied = false), 2000);
    }
  }

  function downloadTranscript() {
    if (!job.text) return;

    const blob = new Blob([job.text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${job.filename?.replace(/\.[^/.]+$/, "") || "transcript"}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  function downloadSRT() {
    if (!job.segments) return;

    let srtContent = "";
    job.segments.forEach((segment, index) => {
      const startTime = formatSRTTime(segment.start);
      const endTime = formatSRTTime(segment.end);
      srtContent += `${index + 1}\n${startTime} --> ${endTime}\n${segment.text.trim()}\n\n`;
    });

    const blob = new Blob([srtContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${job.filename?.replace(/\.[^/.]+$/, "") || "transcript"}.srt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function formatSRTTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${hours.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")},${ms.toString().padStart(3, "0")}`;
  }
</script>

{#if job.status === "completed" && job.text}
  <div class="result-container">
    <div class="result-header">
      <div class="file-info">
        <i class="ri-file-text-line"></i>
        <div>
          <h3>{job.filename || "Transcription"}</h3>
          {#if job.language}
            <span class="language">Language: {job.language.toUpperCase()}</span>
          {/if}
        </div>
      </div>

      <div class="actions">
        <button
          class="action-btn"
          onclick={copyToClipboard}
          title="Copy to clipboard"
        >
          <i class={copied ? "ri-check-line" : "ri-clipboard-line"}></i>
          {copied ? "Copied!" : "Copy"}
        </button>

        <button
          class="action-btn"
          onclick={downloadTranscript}
          title="Download as text"
        >
          <i class="ri-download-line"></i>
          TXT
        </button>

        {#if job.segments && job.segments.length > 0}
          <button
            class="action-btn"
            onclick={downloadSRT}
            title="Download as SRT subtitle"
          >
            <i class="ri-download-line"></i>
            SRT
          </button>

          <button
            class="action-btn toggle"
            onclick={() => (showSegments = !showSegments)}
            title="Toggle segments view"
          >
            <i class={showSegments ? "ri-list-unordered" : "ri-time-line"}></i>
            {showSegments ? "Text" : "Segments"}
          </button>
        {/if}

        {#if onDelete}
          <button
            class="action-btn danger"
            onclick={onDelete}
            title="Delete transcription"
          >
            <i class="ri-delete-bin-line"></i>
          </button>
        {/if}
      </div>
    </div>

    <div class="transcript-content">
      {#if showSegments && job.segments}
        <div class="segments-view">
          {#each job.segments as segment}
            <div class="segment">
              <div class="timestamp">
                {formatTime(segment.start)} - {formatTime(segment.end)}
              </div>
              <div class="segment-text">{segment.text}</div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="text-view">
          <p>{job.text}</p>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .result-container {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    margin: 1rem 0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem;
    border-bottom: 1px solid #f3f4f6;
    background: #f9fafb;
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .file-info i {
    font-size: 1.5rem;
    color: #10b981;
  }

  .file-info h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: #1f2937;
  }

  .language {
    font-size: 0.875rem;
    color: #6b7280;
  }

  .actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .action-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border: 1px solid var(--dashed-border);
    border-radius: 8px;
    background: white;
    color: #374151;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .action-btn:hover {
    background: #f9fafb;
    border-color: #9ca3af;
  }

  .action-btn.toggle {
    background: var(--dashed-border-hover);
    color: white;
    border-color: var(--dashed-border-hover);
  }

  .action-btn.toggle:hover {
    background: #2563eb;
  }

  .action-btn.danger {
    color: #dc2626;
    border-color: #fca5a5;
  }

  .action-btn.danger:hover {
    background: #fef2f2;
    border-color: #f87171;
  }

  .transcript-content {
    max-height: 500px;
    overflow-y: auto;
  }

  .text-view {
    padding: 1.5rem;
  }

  .text-view p {
    margin: 0;
    line-height: 1.6;
    color: #374151;
    font-size: 1rem;
    white-space: pre-wrap;
  }

  .segments-view {
    padding: 1rem;
  }

  .segment {
    display: flex;
    gap: 1rem;
    padding: 0.75rem;
    border-bottom: 1px solid #f3f4f6;
  }

  .segment:last-child {
    border-bottom: none;
  }

  .timestamp {
    flex-shrink: 0;
    font-size: 0.75rem;
    color: #6b7280;
    background: #f3f4f6;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-family: "Monaco", "Menlo", monospace;
    min-width: 5rem;
    text-align: center;
  }

  .segment-text {
    flex: 1;
    color: #374151;
    line-height: 1.5;
  }

  @media (max-width: 768px) {
    .result-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 1rem;
    }

    .actions {
      width: 100%;
      justify-content: flex-start;
    }

    .action-btn {
      font-size: 0.75rem;
      padding: 0.5rem 0.75rem;
    }

    .segment {
      flex-direction: column;
      gap: 0.5rem;
    }

    .timestamp {
      align-self: flex-start;
    }
  }
</style>
