const API_URL = "https://sun-spy-recap.onrender.com";

const videoInput = document.getElementById("videoInput");
const selectButton = document.getElementById("selectButton");
const dropZone = document.getElementById("dropZone");

const fileInfo = document.getElementById("fileInfo");
const progressContainer = document.getElementById("progressContainer");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const progressPercent = document.getElementById("progressPercent");
const statusBox = document.getElementById("statusBox");

const resultSection = document.getElementById("resultSection");
const resultVideo = document.getElementById("resultVideo");
const downloadButton = document.getElementById("downloadButton");
const recapText = document.getElementById("recapText");

let selectedFile = null;
let statusTimer = null;
let retryCount = 0;


/* =========================
   BASIC HELPERS
========================= */

function show(element) {
    if (element) {
        element.classList.remove("hidden");
    }
}

function hide(element) {
    if (element) {
        element.classList.add("hidden");
    }
}

function setProgress(percent, message) {
    const value = Math.max(0, Math.min(100, Number(percent) || 0));

    show(progressContainer);

    if (progressBar) {
        progressBar.style.width = `${value}%`;
    }

    if (progressPercent) {
        progressPercent.textContent = `${Math.round(value)}%`;
    }

    if (progressText) {
        progressText.textContent =
            message || "Processing video...";
    }
}

function formatBytes(bytes) {
    if (!bytes) return "0 B";

    const units = ["B", "KB", "MB", "GB"];

    let size = bytes;
    let index = 0;

    while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index++;
    }

    return `${size.toFixed(2)} ${units[index]}`;
}

function showStatus(message) {
    show(statusBox);

    if (statusBox) {
        statusBox.textContent = message;
    }
}

function showError(message) {
    show(statusBox);

    if (statusBox) {
        statusBox.textContent = `❌ ${message}`;
    }
}


/* =========================
   FILE SELECTION
========================= */

function handleFile(file) {
    if (!file) return;

    if (!file.type.startsWith("video/")) {
        showError("Please select a video file.");
        return;
    }

    selectedFile = file;

    show(fileInfo);

    fileInfo.innerHTML = `
        <strong>🎬 ${file.name}</strong><br>
        Size: ${formatBytes(file.size)}<br>
        Type: ${file.type || "video"}
        <br><br>
        <button id="startRecapButton" type="button">
            🚀 Start Recap
        </button>
    `;

    const startButton =
        document.getElementById("startRecapButton");

    if (startButton) {
        startButton.addEventListener(
            "click",
            startRecap
        );
    }

    showStatus("✅ Video selected. Ready to process.");
}


/* =========================
   FILE INPUT
========================= */

if (videoInput) {
    videoInput.addEventListener(
        "change",
        function () {
            const file = this.files && this.files[0];

            handleFile(file);
        }
    );
}


/*
   Extra fallback for browsers
*/

if (selectButton && videoInput) {
    selectButton.addEventListener(
        "click",
        function () {
            videoInput.click();
        }
    );
}


/* =========================
   DRAG & DROP
========================= */

if (dropZone) {

    dropZone.addEventListener(
        "dragover",
        function (event) {
            event.preventDefault();

            dropZone.classList.add("dragover");
        }
    );

    dropZone.addEventListener(
        "dragleave",
        function () {
            dropZone.classList.remove("dragover");
        }
    );

    dropZone.addEventListener(
        "drop",
        function (event) {
            event.preventDefault();

            dropZone.classList.remove("dragover");

            const files = event.dataTransfer.files;

            if (files && files.length > 0) {
                handleFile(files[0]);
            }
        }
    );
}


/* =========================
   UPLOAD
========================= */

async function uploadVideo(file) {

    showStatus("📤 Uploading video...");
    setProgress(5, "Uploading video...");

    const formData = new FormData();

    formData.append(
        "file",
        file,
        file.name
    );

    const response = await fetch(
        `${API_URL}/api/upload`,
        {
            method: "POST",
            body: formData
        }
    );

    if (!response.ok) {
        const text = await response.text();

        throw new Error(
            text || `Upload failed (${response.status})`
        );
    }

    return await response.json();
}


/* =========================
   START RECAP
========================= */

async function startRecap() {

    if (!selectedFile) {
        showError("Please select a video first.");
        return;
    }

    stopPolling();

    retryCount = 0;

    hide(resultSection);

    setProgress(
        1,
        "Preparing video..."
    );

    try {

        /*
           Upload first
        */

        const uploadResult =
            await uploadVideo(selectedFile);

        const fileId =
            uploadResult.file_id ||
            uploadResult.id ||
            uploadResult.filename ||
            uploadResult.path;

        if (!fileId) {
            throw new Error(
                "Upload succeeded but no file ID was returned."
            );
        }


        /*
           Start recap job
        */

        setProgress(
            10,
            "Starting AI recap..."
        );

        showStatus(
            "🤖 AI is starting the recap..."
        );

        const recapResponse =
            await fetch(
                `${API_URL}/api/recap`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        file_id: fileId
                    })
                }
            );

        if (!recapResponse.ok) {

            const text =
                await recapResponse.text();

            throw new Error(
                text ||
                `Recap request failed (${recapResponse.status})`
            );
        }

        const recapResult =
            await recapResponse.json();

        const jobId =
            recapResult.job_id ||
            recapResult.id ||
            recapResult.job?.id;

        if (!jobId) {
            throw new Error(
                "Recap started but no job ID was returned."
            );
        }


        /*
           Begin status polling
        */

        showStatus(
            "🎬 Processing started..."
        );

        monitorJob(jobId);

    } catch (error) {

        console.error(error);

        showError(
            error.message ||
            "Unable to start video processing."
        );
    }
}


/* =========================
   JOB MONITOR
========================= */

function monitorJob(jobId) {

    stopPolling();

    retryCount = 0;

    checkJobStatus(jobId);

    statusTimer =
        setInterval(
            function () {
                checkJobStatus(jobId);
            },
            4000
        );
}


/* =========================
   STATUS
========================= */

async function checkJobStatus(jobId) {

    try {

        const response =
            await fetch(
                `${API_URL}/api/status/${jobId}`,
                {
                    method: "GET",
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            throw new Error(
                `Status ${response.status}`
            );
        }

        const data =
            await response.json();

        retryCount = 0;

        const job =
            data.job || data;

        const status =
            String(
                job.status || ""
            ).toUpperCase();

        const progress =
            Number(
                job.progress || 0
            );

        const message =
            job.message ||
            job.stage ||
            "AI is processing your video...";


        /*
           Update UI
        */

        setProgress(
            progress,
            message
        );

        showStatus(
            `🎬 ${message}`
        );


        /*
           COMPLETED
        */

        if (
            status === "COMPLETED" ||
            status === "COMPLETE" ||
            status === "DONE"
        ) {

            stopPolling();

            setProgress(
                100,
                "Completed!"
            );

            showStatus(
                "🎉 Recap completed successfully!"
            );

            showResult(job);

            return;
        }


        /*
           FAILED
        */

        if (
            status === "FAILED" ||
            status === "ERROR"
        ) {

            stopPolling();

            showError(
                job.error ||
                job.message ||
                "Video processing failed."
            );

            return;
        }

    } catch (error) {

        console.warn(
            "Temporary status connection error:",
            error
        );

        retryCount++;

        /*
           IMPORTANT:
           Do not stop processing.
        */

        showStatus(
            `🔄 Connection temporarily unavailable — retrying (${retryCount})...`
        );

        setProgress(
            Math.max(
                1,
                Math.min(
                    98,
                    retryCount
                )
            ),
            "Processing continues..."
        );
    }
}


/* =========================
   RESULT
========================= */

function showResult(job) {

    show(resultSection);

    const output =
        job.output_file ||
        job.output ||
        job.video_url ||
        job.result_url ||
        job.file_url;

    if (output) {

        let videoUrl = output;

        /*
           Convert relative path
           to backend URL
        */

        if (
            !output.startsWith("http://") &&
            !output.startsWith("https://")
        ) {

            videoUrl =
                `${API_URL}/${output
                    .replace(/^\/+/, "")}`;
        }

        if (resultVideo) {
            resultVideo.src = videoUrl;
            resultVideo.load();
        }

        if (downloadButton) {
            downloadButton.href = videoUrl;
            downloadButton.download =
                "sun-spy-recap.mp4";
        }
    }

    const text =
        job.recap_text ||
        job.summary ||
        job.recap ||
        "";

    if (recapText) {
        recapText.textContent = text;
    }
}


/* =========================
   STOP POLLING
========================= */

function stopPolling() {

    if (statusTimer) {

        clearInterval(statusTimer);

        statusTimer = null;
    }
}


/* =========================
   INITIAL STATE
========================= */

hide(fileInfo);
hide(progressContainer);
hide(statusBox);
hide(resultSection);
