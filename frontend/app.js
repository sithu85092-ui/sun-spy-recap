const API_URL = "https://sun-spy-recap.onrender.com";

const CHUNK_SIZE = 5 * 1024 * 1024;
const MAX_RETRIES = 3;
const POLL_INTERVAL = 3000;

// --------------------------------------------------
// DOM
// --------------------------------------------------

const fileInput =
    document.getElementById("fileInput") ||
    document.querySelector('input[type="file"]');

const uploadButton =
    document.getElementById("uploadButton") ||
    document.getElementById("uploadBtn") ||
    document.querySelector(".upload-btn");

const statusBox =
    document.getElementById("statusBox") ||
    document.getElementById("status");

const progressBar =
    document.getElementById("progressBar");

const progressText =
    document.getElementById("progressText");

const resultBox =
    document.getElementById("resultBox");

let selectedFile = null;
let pollingTimer = null;

// --------------------------------------------------
// HELPERS
// --------------------------------------------------

function showStatus(message, type = "") {
    if (!statusBox) return;

    statusBox.textContent = message;
    statusBox.className = "status";

    if (type) {
        statusBox.classList.add(type);
    }
}

function setProgress(percent, message = "") {
    const value = Math.max(
        0,
        Math.min(100, Number(percent) || 0)
    );

    if (progressBar) {
        progressBar.value = value;
        progressBar.style.width = `${value}%`;
    }

    if (progressText) {
        progressText.textContent =
            `${Math.round(value)}%`;
    }

    if (message) {
        showStatus(message);
    }
}

function stopPolling() {
    if (pollingTimer) {
        clearTimeout(pollingTimer);
        pollingTimer = null;
    }
}

function sleep(ms) {
    return new Promise(resolve =>
        setTimeout(resolve, ms)
    );
}

function showError(error) {
    const message =
        error instanceof Error
            ? error.message
            : String(error);

    showStatus(
        `❌ ${message}`,
        "error"
    );

    setProgress(
        0,
        "Processing stopped."
    );

    console.error(
        "SUN SPY RECAP ERROR:",
        message
    );
}

function showResult(outputFile, recapText) {
    stopPolling();

    if (!resultBox) {
        return;
    }

    resultBox.style.display = "block";

    const fileName =
        outputFile ||
        "";

    const videoUrl =
        fileName.startsWith("http")
            ? fileName
            : `${API_URL}/api/files/${encodeURIComponent(fileName)}`;

    resultBox.innerHTML = `
        <div class="result-content">

            <h2>🎉 Recap Complete!</h2>

            <video
                controls
                playsinline
                preload="metadata"
                style="
                    width:100%;
                    max-width:420px;
                    border-radius:16px;
                    display:block;
                    margin:15px auto;
                "
            >
                <source
                    src="${videoUrl}"
                    type="video/mp4"
                >
                Your browser does not support video playback.
            </video>

            ${
                recapText
                    ? `
                    <div class="recap-text">
                        <h3>📝 Burmese Recap</h3>
                        <p>${escapeHtml(recapText)}</p>
                    </div>
                    `
                    : ""
            }

            <a
                href="${videoUrl}"
                target="_blank"
                rel="noopener"
                download
                class="download-btn"
            >
                ⬇️ Download Recap Video
            </a>

        </div>
    `;
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// --------------------------------------------------
// API REQUEST WITH RETRY
// --------------------------------------------------

async function fetchWithRetry(
    url,
    options = {},
    retries = MAX_RETRIES
) {
    let lastError;

    for (
        let attempt = 1;
        attempt <= retries;
        attempt++
    ) {
        try {
            const response =
                await fetch(url, {
                    ...options,
                    cache: "no-store"
                });

            if (response.ok) {
                return response;
            }

            const text =
                await response.text();

            throw new Error(
                text ||
                `HTTP ${response.status}`
            );

        } catch (error) {

            lastError = error;

            console.warn(
                `Request failed (${attempt}/${retries}):`,
                url,
                error
            );

            if (attempt < retries) {
                await sleep(1500 * attempt);
            }
        }
    }

    throw lastError ||
        new Error("Network request failed.");
}

// --------------------------------------------------
// FILE SELECTION
// --------------------------------------------------

if (fileInput) {

    fileInput.addEventListener(
        "change",
        event => {

            const file =
                event.target.files &&
                event.target.files[0];

            if (!file) {
                selectedFile = null;
                return;
            }

            selectedFile = file;

            console.log(
                "Selected video:",
                file.name,
                file.size
            );

            showStatus(
                `🎬 Selected: ${file.name}`
            );

            setProgress(
                0,
                `Selected: ${file.name}`
            );
        }
    );
}

// --------------------------------------------------
// UPLOAD INIT
// --------------------------------------------------

async function initUpload(file) {

    const formData =
        new FormData();

    formData.append(
        "filename",
        file.name
    );

    formData.append(
        "file_size",
        String(file.size)
    );

    const response =
        await fetchWithRetry(
            `${API_URL}/api/upload/init`,
            {
                method: "POST",
                body: formData
            }
        );

    const data =
        await response.json();

    if (!data.upload_id) {
        throw new Error(
            data.detail ||
            data.message ||
            "Upload initialization failed."
        );
    }

    return data;
}

// --------------------------------------------------
// UPLOAD CHUNK
// --------------------------------------------------

async function uploadChunk(
    uploadId,
    chunkIndex,
    blob
) {
    const formData =
        new FormData();

    formData.append(
        "upload_id",
        uploadId
    );

    formData.append(
        "chunk_index",
        String(chunkIndex)
    );

    formData.append(
        "chunk",
        blob,
        `chunk_${chunkIndex}`
    );

    const response =
        await fetchWithRetry(
            `${API_URL}/api/upload/chunk`,
            {
                method: "POST",
                body: formData
            }
        );

    return await response.json();
}

// --------------------------------------------------
// COMPLETE UPLOAD
// --------------------------------------------------

async function completeUpload(
    uploadId,
    filename,
    totalChunks
) {
    const formData =
        new FormData();

    formData.append(
        "upload_id",
        uploadId
    );

    formData.append(
        "filename",
        filename
    );

    formData.append(
        "total_chunks",
        String(totalChunks)
    );

    const response =
        await fetchWithRetry(
            `${API_URL}/api/upload/complete`,
            {
                method: "POST",
                body: formData
            }
        );

    const data =
        await response.json();

    if (!data.filename) {
        throw new Error(
            data.detail ||
            data.message ||
            "Upload completion failed."
        );
    }

    return data;
}

// --------------------------------------------------
// FULL VIDEO UPLOAD
// --------------------------------------------------

async function uploadVideo(file) {

    if (!file) {
        throw new Error(
            "Please select a video first."
        );
    }

    if (!file.type.startsWith("video/")) {
        throw new Error(
            "Please select a valid video file."
        );
    }

    showStatus(
        "☁️ Preparing video upload..."
    );

    setProgress(
        1,
        "Preparing video upload..."
    );

    // INIT

    const initData =
        await initUpload(file);

    const uploadId =
        initData.upload_id;

    // CHUNKS

    const totalChunks =
        Math.ceil(
            file.size / CHUNK_SIZE
        );

    for (
        let index = 0;
        index < totalChunks;
        index++
    ) {

        const start =
            index * CHUNK_SIZE;

        const end =
            Math.min(
                start + CHUNK_SIZE,
                file.size
            );

        const chunk =
            file.slice(start, end);

        let success = false;
        let lastError = null;

        for (
            let attempt = 1;
            attempt <= MAX_RETRIES;
            attempt++
        ) {

            try {

                await uploadChunk(
                    uploadId,
                    index,
                    chunk
                );

                success = true;
                break;

            } catch (error) {

                lastError = error;

                console.warn(
                    `Chunk ${index} failed ` +
                    `(${attempt}/${MAX_RETRIES})`,
                    error
                );

                if (
                    attempt < MAX_RETRIES
                ) {
                    await sleep(
                        1500 * attempt
                    );
                }
            }
        }

        if (!success) {
            throw lastError ||
                new Error(
                    `Upload failed at chunk ${index}.`
                );
        }

        const progress =
            5 +
            (
                ((index + 1) /
                totalChunks) * 30
            );

        setProgress(
            progress,
            `⬆️ Uploading video... ` +
            `${index + 1}/${totalChunks}`
        );
    }

    // COMPLETE

    setProgress(
        38,
        "🔧 Finalizing uploaded video..."
    );

    const completeData =
        await completeUpload(
            uploadId,
            file.name,
            totalChunks
        );

    return {
        uploadId:
            completeData.upload_id ||
            uploadId,

        filename:
            completeData.filename,

        path:
            completeData.path
    };
}

// --------------------------------------------------
// START RECAP
// --------------------------------------------------

async function startRecap(
    uploadData
) {

    if (!uploadData) {
        throw new Error(
            "Upload information is missing."
        );
    }

    if (
        !uploadData.uploadId ||
        !uploadData.filename
    ) {
        throw new Error(
            "Invalid uploaded video information."
        );
    }

    showStatus(
        "🤖 Starting AI video analysis..."
    );

    setProgress(
        40,
        "🤖 Starting AI video analysis..."
    );

    const response =
        await fetchWithRetry(
            `${API_URL}/api/recap`,
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify({
                    upload_id:
                        uploadData.uploadId,

                    filename:
                        uploadData.filename
                })
            }
        );

    const data =
        await response.json();

    if (!data.job_id) {
        throw new Error(
            data.detail ||
            data.message ||
            "Could not start recap job."
        );
    }

    return data.job_id;
}

// --------------------------------------------------
// CHECK JOB STATUS
// --------------------------------------------------

async function checkJobStatus(jobId) {

    try {

        const response =
            await fetch(
                `${API_URL}/api/status/${encodeURIComponent(jobId)}`,
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {

            throw new Error(
                `Unable to get processing status (${response.status})`
            );
        }

        const data =
            await response.json();

        const job =
            data.job || data;

        if (!job) {
            throw new Error(
                "Invalid processing status."
            );
        }

        const status =
            String(
                job.status || ""
            ).toUpperCase();

        const progress =
            Number(
                job.progress ?? 0
            );

        const message =
            job.message ||
            "Processing video...";

        // CURRENT PROGRESS

        setProgress(
            progress,
            message
        );

        // COMPLETED

        if (
            status === "COMPLETED" ||
            status === "COMPLETE"
        ) {

            stopPolling();

            setProgress(
                100,
                "🎉 Recap completed successfully!"
            );

            showStatus(
                "🎉 Recap completed successfully!",
                "success"
            );

            showResult(
                job.output_file ||
                job.output ||
                job.filename,

                job.recap_text ||
                job.summary ||
                ""
            );

            return true;
        }

        // FAILED
        // IMPORTANT:
        // return instead of throw so the catch block
        // does not hide the real backend error.

        if (
            status === "FAILED" ||
            status === "ERROR"
        ) {

            stopPolling();

            const realError =
                job.error ||
                job.message ||
                "Video processing failed.";

            setProgress(
                0,
                "Processing stopped."
            );

            showError(
                realError
            );

            return true;
        }

        // CONTINUE POLLING

        pollingTimer =
            setTimeout(
                () => checkJobStatus(jobId),
                POLL_INTERVAL
            );

        return false;

    } catch (error) {

        console.warn(
            "Status check failed:",
            error
        );

        // Temporary network/server issue.
        // Do not immediately mark the video as failed.

        pollingTimer =
            setTimeout(
                () => checkJobStatus(jobId),
                5000
            );

        return false;
    }
}

// --------------------------------------------------
// START POLLING
// --------------------------------------------------

function pollJob(jobId) {

    stopPolling();

    return checkJobStatus(
        jobId
    );
}

// --------------------------------------------------
// MAIN PROCESS
// --------------------------------------------------

async function processVideo() {

    stopPolling();

    if (!selectedFile) {

        if (fileInput?.files?.[0]) {
            selectedFile =
                fileInput.files[0];
        }
    }

    if (!selectedFile) {

        showError(
            "Please select a video first."
        );

        return;
    }

    try {

        // RESET UI

        if (resultBox) {
            resultBox.style.display =
                "none";

            resultBox.innerHTML =
                "";
        }

        setProgress(
            0,
            "🎬 Starting..."
        );

        // UPLOAD

        const uploadData =
            await uploadVideo(
                selectedFile
            );

        console.log(
            "Upload completed:",
            uploadData
        );

        // RECAP

        const jobId =
            await startRecap(
                uploadData
            );

        console.log(
            "Recap job:",
            jobId
        );

        // POLLING

        await pollJob(
            jobId
        );

    } catch (error) {

        console.error(
            "SUN SPY RECAP FAILED:",
            error
        );

        showError(
            error
        );
    }
}

// --------------------------------------------------
// BUTTON EVENTS
// --------------------------------------------------

if (uploadButton) {

    uploadButton.addEventListener(
        "click",
        event => {

            event.preventDefault();

            processVideo();
        }
    );
}

// Support common button IDs

const possibleButtons = [
    "startButton",
    "startRecap",
    "recapButton",
    "processButton",
    "uploadBtn"
];

possibleButtons.forEach(id => {

    const button =
        document.getElementById(id);

    if (
        button &&
        button !== uploadButton
    ) {

        button.addEventListener(
            "click",
            event => {

                event.preventDefault();

                processVideo();
            }
        );
    }
});

// --------------------------------------------------
// GLOBAL FUNCTION
// --------------------------------------------------

window.processVideo =
    processVideo;

window.startRecap =
    startRecap;

window.uploadVideo =
    uploadVideo;

window.checkJobStatus =
    checkJobStatus;

window.pollJob =
    pollJob;

// --------------------------------------------------
// INITIAL STATUS
// --------------------------------------------------

console.log(
    "SUN SPY RECAP frontend loaded."
);

console.log(
    "API:",
    API_URL
);
