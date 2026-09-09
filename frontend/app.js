const API_URL = "https://sun-spy-recap.onrender.com";

const CHUNK_SIZE = 5 * 1024 * 1024;

let selectedFile = null;
let currentJobId = null;
let pollingTimer = null;


// =====================================================
// DOM
// =====================================================

const videoInput =
    document.getElementById("videoInput");

const selectButton =
    document.getElementById("selectButton");

const uploadButton =
    document.getElementById("uploadButton");

const dropZone =
    document.getElementById("dropZone");

const fileInfo =
    document.getElementById("fileInfo");

const inputPreviewContainer =
    document.getElementById("inputPreviewContainer");

const inputPreview =
    document.getElementById("inputPreview");

const progressContainer =
    document.getElementById("progressContainer");

const progressBar =
    document.getElementById("progressBar");

const progressPercent =
    document.getElementById("progressPercent");

const progressText =
    document.getElementById("progressText");

const statusBox =
    document.getElementById("statusBox");

const resultSection =
    document.getElementById("resultSection");

const resultVideo =
    document.getElementById("resultVideo");

const downloadButton =
    document.getElementById("downloadButton");

const recapText =
    document.getElementById("recapText");


// =====================================================
// STATUS
// =====================================================

function showStatus(message, type = "") {

    if (!statusBox) return;

    statusBox.className = "status-box";

    if (type) {
        statusBox.classList.add(type);
    }

    statusBox.classList.remove("hidden");

    statusBox.textContent = message;
}


// =====================================================
// PROGRESS
// =====================================================

function setProgress(percent, message) {

    const value = Math.max(
        0,
        Math.min(100, Number(percent) || 0)
    );

    if (progressContainer) {
        progressContainer.classList.remove("hidden");
    }

    if (progressBar) {
        progressBar.style.width = `${value}%`;
    }

    if (progressPercent) {
        progressPercent.textContent =
            `${Math.round(value)}%`;
    }

    if (progressText && message) {
        progressText.textContent = message;
    }
}


// =====================================================
// HELPERS
// =====================================================

function sleep(ms) {

    return new Promise(
        resolve => setTimeout(resolve, ms)
    );
}


function formatBytes(bytes) {

    if (!bytes) return "0 B";

    const units = [
        "B",
        "KB",
        "MB",
        "GB"
    ];

    const index = Math.floor(
        Math.log(bytes) / Math.log(1024)
    );

    return (
        (bytes / Math.pow(1024, index))
        .toFixed(1)
        + " "
        + units[index]
    );
}


function escapeHTML(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


async function requestJSON(
    url,
    options = {},
    retries = 2
) {

    let lastError;

    for (
        let attempt = 0;
        attempt <= retries;
        attempt++
    ) {

        try {

            const response =
                await fetch(
                    url,
                    options
                );

            let data = {};

            try {

                data =
                    await response.json();

            } catch {

                data = {};

            }


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    data.error ||
                    data.message ||
                    `HTTP ${response.status}`
                );
            }


            return data;

        } catch (error) {

            lastError = error;

            if (attempt < retries) {

                await sleep(
                    1500 * (attempt + 1)
                );

            }
        }
    }

    throw lastError;
}


// =====================================================
// SELECT VIDEO
// =====================================================

if (selectButton && videoInput) {

    selectButton.addEventListener(
        "click",
        () => {

            videoInput.click();

        }
    );
}


if (videoInput) {

    videoInput.addEventListener(
        "change",
        event => {

            const file =
                event.target.files?.[0];

            if (file) {

                handleFile(file);

            }

        }
    );
}


// =====================================================
// HANDLE FILE
// =====================================================

function handleFile(file) {

    if (!file.type.startsWith("video/")) {

        showStatus(
            "❌ Please select a video file.",
            "error"
        );

        return;
    }


    selectedFile = file;


    if (fileInfo) {

        fileInfo.classList.remove(
            "hidden"
        );

        fileInfo.innerHTML = `
            <strong>
                ${escapeHTML(file.name)}
            </strong>
            <br>
            <small>
                ${formatBytes(file.size)}
            </small>
        `;
    }


    if (
        inputPreview &&
        inputPreviewContainer
    ) {

        const url =
            URL.createObjectURL(file);

        inputPreview.src = url;

        inputPreviewContainer
            .classList
            .remove("hidden");
    }


    if (uploadButton) {

        uploadButton.disabled = false;

        uploadButton.textContent =
            "🚀 Start AI Recap";
    }


    showStatus(
        "✅ Video selected. Press Start AI Recap.",
        "success"
    );


    setProgress(
        0,
        "Ready"
    );
}


// =====================================================
// DRAG & DROP
// =====================================================

if (dropZone) {

    dropZone.addEventListener(
        "dragover",
        event => {

            event.preventDefault();

            dropZone.classList.add(
                "dragging"
            );

        }
    );


    dropZone.addEventListener(
        "dragleave",
        () => {

            dropZone.classList.remove(
                "dragging"
            );

        }
    );


    dropZone.addEventListener(
        "drop",
        event => {

            event.preventDefault();

            dropZone.classList.remove(
                "dragging"
            );


            const file =
                event.dataTransfer
                    .files?.[0];


            if (file) {

                handleFile(file);

            }

        }
    );
}


// =====================================================
// START BUTTON
// =====================================================

if (uploadButton) {

    uploadButton.addEventListener(
        "click",
        async () => {

            if (!selectedFile) {

                showStatus(
                    "❌ Please select a video first.",
                    "error"
                );

                return;
            }


            uploadButton.disabled = true;

            uploadButton.textContent =
                "⏳ Processing...";


            if (resultSection) {

                resultSection
                    .classList
                    .add("hidden");
            }


            try {

                await processVideo(
                    selectedFile
                );

            } catch (error) {

                console.error(
                    "PROCESS ERROR:",
                    error
                );


                stopPolling();


                showStatus(
                    `❌ ${
                        error.message ||
                        "Video processing failed."
                    }`,
                    "error"
                );


                uploadButton.disabled =
                    false;

                uploadButton.textContent =
                    "🚀 Try Again";
            }

        }
    );
}


// =====================================================
// MAIN PROCESS
// =====================================================

async function processVideo(file) {

    setProgress(
        2,
        "Connecting to SUN SPY server..."
    );


    showStatus(
        "🤖 Starting AI video analysis..."
    );


    // ---------------------------------
    // HEALTH
    // ---------------------------------

    try {

        await requestJSON(
            `${API_URL}/api/health`,
            {},
            2
        );

    } catch (error) {

        console.warn(
            "Health check:",
            error
        );
    }


    // ---------------------------------
    // INIT
    // ---------------------------------

    setProgress(
        5,
        "Preparing video upload..."
    );


    const initForm =
        new FormData();


    initForm.append(
        "filename",
        file.name
    );


    initForm.append(
        "file_size",
        file.size
    );


    const initData =
        await requestJSON(
            `${API_URL}/api/upload/init`,
            {
                method: "POST",
                body: initForm
            },
            3
        );


    const uploadId =
        initData.upload_id;


    if (!uploadId) {

        throw new Error(
            "Server did not return upload ID."
        );
    }


    console.log(
        "UPLOAD ID:",
        uploadId
    );


    // ---------------------------------
    // CHUNKS
    // ---------------------------------

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
            file.slice(
                start,
                end
            );


        let success = false;


        for (
            let attempt = 0;
            attempt < 3;
            attempt++
        ) {

            try {

                const form =
                    new FormData();


                form.append(
                    "upload_id",
                    uploadId
                );


                form.append(
                    "chunk_index",
                    index
                );


                form.append(
                    "chunk",
                    chunk,
                    file.name
                );


                await requestJSON(
                    `${API_URL}/api/upload/chunk`,
                    {
                        method: "POST",
                        body: form
                    },
                    0
                );


                success = true;

                break;


            } catch (error) {

                console.warn(
                    "Chunk failed:",
                    index,
                    error
                );


                if (attempt < 2) {

                    await sleep(2000);

                }
            }
        }


        if (!success) {

            throw new Error(
                `Upload failed at chunk ${
                    index + 1
                }/${totalChunks}.`
            );
        }


        const percent =
            5 +
            (
                (index + 1) /
                totalChunks
            ) * 30;


        setProgress(
            percent,
            `Uploading video... ${
                index + 1
            }/${totalChunks}`
        );
    }


    // ---------------------------------
    // COMPLETE
    // ---------------------------------

    setProgress(
        38,
        "Combining video chunks..."
    );


    const completeForm =
        new FormData();


    completeForm.append(
        "upload_id",
        uploadId
    );


    completeForm.append(
        "filename",
        file.name
    );


    completeForm.append(
        "total_chunks",
        totalChunks
    );


    const completeData =
        await requestJSON(
            `${API_URL}/api/upload/complete`,
            {
                method: "POST",
                body: completeForm
            },
            3
        );


    if (!completeData.filename) {

        throw new Error(
            "Server could not complete upload."
        );
    }


    console.log(
        "UPLOAD COMPLETE:",
        completeData
    );


    // ---------------------------------
    // START RECAP
    // ---------------------------------

    setProgress(
        42,
        "Starting AI video analysis..."
    );


    showStatus(
        "🧠 AI is analyzing the entire video..."
    );


    const recapData =
        await requestJSON(
            `${API_URL}/api/recap`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({

                    upload_id:
                        completeData.upload_id ||
                        uploadId,

                    filename:
                        completeData.filename

                })
            },
            3
        );


    currentJobId =
        recapData.job_id;


    if (!currentJobId) {

        throw new Error(
            "Server did not return job ID."
        );
    }


    console.log(
        "JOB ID:",
        currentJobId
    );


    startPolling(
        currentJobId
    );
}


// =====================================================
// POLLING
// =====================================================

function startPolling(jobId) {

    stopPolling();

    checkJobStatus(jobId);
}


function stopPolling() {

    if (pollingTimer) {

        clearTimeout(
            pollingTimer
        );

        pollingTimer = null;
    }
}


// =====================================================
// CHECK STATUS
// =====================================================

async function checkJobStatus(jobId) {

    try {

        const data =
            await requestJSON(
                `${API_URL}/api/status/${jobId}`,
                {
                    cache: "no-store"
                },
                2
            );


        console.log(
            "STATUS RESPONSE:",
            data
        );


        // IMPORTANT:
        // Backend returns:
        // { success: true, job: {...} }

        const job =
            data.job || data;


        if (!job) {

            throw new Error(
                "Invalid job status."
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


        setProgress(
            progress,
            message
        );


        // ---------------------------------
        // COMPLETED
        // ---------------------------------

        if (
            status === "COMPLETED" ||
            status === "COMPLETE" ||
            status === "SUCCESS"
        ) {

            stopPolling();


            setProgress(
                100,
                "Complete!"
            );


            showStatus(
                "🎉 Your AI recap is ready!",
                "success"
            );


            showResult(
                job
            );


            uploadButton.disabled =
                false;


            uploadButton.textContent =
                "🚀 Start Another Recap";


            return;
        }


        // ---------------------------------
        // FAILED
        // ---------------------------------

        if (
            status === "FAILED" ||
            status === "ERROR"
        ) {

            stopPolling();


            const error =
                job.error ||
                job.message ||
                "Video processing failed.";


            console.error(
                "BACKEND ERROR:",
                error
            );


            showStatus(
                `❌ ${error}`,
                "error"
            );


            uploadButton.disabled =
                false;


            uploadButton.textContent =
                "🚀 Try Again";


            return;
        }


        // ---------------------------------
        // KEEP POLLING
        // ---------------------------------

        pollingTimer =
            setTimeout(
                () =>
                    checkJobStatus(
                        jobId
                    ),
                3000
            );


    } catch (error) {

        console.error(
            "STATUS ERROR:",
            error
        );


        showStatus(
            "⏳ Checking server... retrying..."
        );


        pollingTimer =
            setTimeout(
                () =>
                    checkJobStatus(
                        jobId
                    ),
                5000
            );
    }
}


// =====================================================
// RESULT
// =====================================================

function showResult(job) {

    if (!resultSection) {

        console.error(
            "resultSection missing."
        );

        return;
    }


    resultSection
        .classList
        .remove("hidden");


    const filename =
        job.output_file ||
        job.output_filename ||
        job.result_file ||
        job.result_filename;


    if (filename) {

        const videoURL =
            `${API_URL}/api/files/${encodeURIComponent(
                filename
            )}`;


        if (resultVideo) {

            resultVideo.src =
                videoURL;

            resultVideo.load();
        }


        if (downloadButton) {

            downloadButton.href =
                videoURL;

            downloadButton.download =
                filename;
        }
    }


    if (recapText) {

        recapText.textContent =
            job.recap_text ||
            "Your Burmese recap is ready.";
    }


    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


// =====================================================
// INITIAL STATE
// =====================================================

if (uploadButton) {

    uploadButton.disabled = true;

    uploadButton.textContent =
        "🚀 Start AI Recap";
}


console.log(
    "☀️ SUN SPY RECAP loaded"
);

console.log(
    "API:",
    API_URL
);
