const API_URL = "https://sun-spy-recap.onrender.com";
const CHUNK_SIZE = 5 * 1024 * 1024;
const MAX_RETRIES = 3;

const videoInput = document.getElementById("videoInput");
const selectButton = document.getElementById("selectButton");
const dropZone = document.getElementById("dropZone");

const fileInfo = document.getElementById("fileInfo");
const progressContainer = document.getElementById("progressContainer");
const progressText = document.getElementById("progressText");
const progressPercent = document.getElementById("progressPercent");
const progressBar = document.getElementById("progressBar");
const statusBox = document.getElementById("statusBox");

const resultSection = document.getElementById("resultSection");
const resultVideo = document.getElementById("resultVideo");
const downloadButton = document.getElementById("downloadButton");
const recapText = document.getElementById("recapText");

let selectedFile = null;
let previewURL = null;


/* =========================
   BASIC UI
========================= */

function showStatus(message, type = "info") {
    statusBox.classList.remove("hidden");

    statusBox.textContent = message;

    statusBox.className = "status-box";

    if (type === "error") {
        statusBox.classList.add("error");
    } else if (type === "success") {
        statusBox.classList.add("success");
    }
}


function setProgress(percent, message) {
    const safePercent = Math.max(0, Math.min(100, percent));

    progressContainer.classList.remove("hidden");

    progressText.textContent = message;
    progressPercent.textContent = `${Math.round(safePercent)}%`;
    progressBar.style.width = `${safePercent}%`;
}


function formatBytes(bytes) {
    if (!bytes) return "0 B";

    const units = ["B", "KB", "MB", "GB"];

    let i = 0;
    let size = bytes;

    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
    }

    return `${size.toFixed(2)} ${units[i]}`;
}


/* =========================
   FILE SELECTION
========================= */

if (selectButton) {
    selectButton.addEventListener("click", () => {
        videoInput.click();
    });
}


if (videoInput) {
    videoInput.addEventListener("change", () => {
        if (videoInput.files && videoInput.files.length > 0) {
            handleFile(videoInput.files[0]);
        }
    });
}


if (dropZone) {
    dropZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropZone.classList.remove("dragover");

        const files = event.dataTransfer.files;

        if (files && files.length > 0) {
            handleFile(files[0]);
        }
    });
}


function handleFile(file) {
    if (!file.type.startsWith("video/")) {
        showStatus("❌ Please select a video file.", "error");
        return;
    }

    selectedFile = file;

    fileInfo.classList.remove("hidden");

    fileInfo.textContent =
        `Selected: ${file.name} • ${formatBytes(file.size)}`;

    showStatus("Video selected. Preparing upload...", "info");

    resultSection.classList.add("hidden");

    createPreview(file);

    startUpload();
}


/* =========================
   LOCAL VIDEO PREVIEW
========================= */

function createPreview(file) {
    if (previewURL) {
        URL.revokeObjectURL(previewURL);
    }

    previewURL = URL.createObjectURL(file);

    const preview = document.getElementById("inputPreview");

    if (preview) {
        preview.src = previewURL;
        preview.load();
    }
}


/* =========================
   FETCH WITH RETRY
========================= */

async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
    let lastError = null;

    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            const response = await fetch(url, options);

            if (response.ok) {
                return response;
            }

            const text = await response.text();

            throw new Error(
                `HTTP ${response.status}: ${text || response.statusText}`
            );

        } catch (error) {
            lastError = error;

            if (attempt < retries) {
                await sleep(1500 * attempt);
            }
        }
    }

    throw lastError;
}


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


/* =========================
   UPLOAD
========================= */

async function startUpload() {
    if (!selectedFile) {
        return;
    }

    try {
        resultSection.classList.add("hidden");

        setProgress(0, "Preparing upload...");
        showStatus("🎬 Connecting to SUN SPY RECAP...", "info");


        /* -------------------------
           STEP 1: INIT
        ------------------------- */

        const initForm = new FormData();

        initForm.append("filename", selectedFile.name);
        initForm.append("file_size", selectedFile.size.toString());


        const initResponse = await fetchWithRetry(
            `${API_URL}/api/upload/init`,
            {
                method: "POST",
                body: initForm
            }
        );


        const initData = await initResponse.json();


        if (!initData.upload_id) {
            throw new Error(
                initData.detail ||
                initData.message ||
                "Upload initialization failed."
            );
        }


        const uploadId = initData.upload_id;


        /* -------------------------
           STEP 2: CHUNKS
        ------------------------- */

        const totalChunks =
            Math.ceil(selectedFile.size / CHUNK_SIZE);


        for (let index = 0; index < totalChunks; index++) {

            const start = index * CHUNK_SIZE;
            const end = Math.min(
                start + CHUNK_SIZE,
                selectedFile.size
            );

            const chunk = selectedFile.slice(start, end);

            const chunkForm = new FormData();

            chunkForm.append(
                "upload_id",
                uploadId
            );

            chunkForm.append(
                "chunk_index",
                index.toString()
            );

            chunkForm.append(
                "chunk",
                chunk,
                selectedFile.name
            );


            let uploaded = false;
            let lastError = null;


            for (
                let attempt = 1;
                attempt <= MAX_RETRIES;
                attempt++
            ) {

                try {

                    const response = await fetch(
                        `${API_URL}/api/upload/chunk`,
                        {
                            method: "POST",
                            body: chunkForm
                        }
                    );


                    if (!response.ok) {

                        const text =
                            await response.text();

                        throw new Error(
                            `Chunk ${index + 1}/${totalChunks} failed: HTTP ${response.status} ${text}`
                        );
                    }


                    uploaded = true;
                    break;


                } catch (error) {

                    lastError = error;

                    if (attempt < MAX_RETRIES) {
                        await sleep(1500 * attempt);
                    }
                }
            }


            if (!uploaded) {
                throw lastError ||
                    new Error(
                        `Failed to upload chunk ${index + 1}`
                    );
            }


            const percent =
                ((index + 1) / totalChunks) * 60;


            setProgress(
                percent,
                `Uploading video... ${index + 1}/${totalChunks}`
            );

            showStatus(
                `📤 Uploading video... ${index + 1}/${totalChunks}`,
                "info"
            );
        }


        /* -------------------------
           STEP 3: COMPLETE
        ------------------------- */

        setProgress(
            65,
            "Assembling uploaded video..."
        );

        showStatus(
            "🔧 Assembling video...",
            "info"
        );


        const completeForm = new FormData();

        completeForm.append(
            "upload_id",
            uploadId
        );

        completeForm.append(
            "filename",
            selectedFile.name
        );

        completeForm.append(
            "total_chunks",
            totalChunks.toString()
        );


        const completeResponse =
            await fetchWithRetry(
                `${API_URL}/api/upload/complete`,
                {
                    method: "POST",
                    body: completeForm
                }
            );


        const completeData =
            await completeResponse.json();


        if (!completeData.upload_id) {
            throw new Error(
                completeData.detail ||
                completeData.message ||
                "Could not complete upload."
            );
        }


        /* -------------------------
           STEP 4: START RECAP
        ------------------------- */

        setProgress(
            70,
            "Starting AI recap..."
        );

        showStatus(
            "🤖 Starting AI video analysis...",
            "info"
        );


        const recapResponse =
            await fetchWithRetry(
                `${API_URL}/api/recap`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        upload_id:
                            completeData.upload_id,

                        filename:
                            completeData.filename
                    })
                }
            );


        const recapData =
            await recapResponse.json();


        const jobId =
            recapData.job_id ||
            recapData.id ||
            recapData.job?.id;


        if (!jobId) {
            throw new Error(
                recapData.detail ||
                recapData.message ||
                "Could not start recap job."
            );
        }


        /* -------------------------
           STEP 5: POLL STATUS
        ------------------------- */

        await pollJob(jobId);


    } catch (error) {

        console.error(
            "SUN SPY RECAP ERROR:",
            error
        );

        setProgress(
            0,
            "Processing stopped."
        );

        showStatus(
            `❌ ${error.message || "Processing failed."}`,
            "error"
        );
    }
}


/* =========================
   JOB STATUS
========================= */

async function pollJob(jobId) {

    let temporaryErrors = 0;

    while (true) {

        try {

            const response =
                await fetch(
                    `${API_URL}/api/status/${jobId}`,
                    {
                        cache: "no-store"
                    }
                );


            if (!response.ok) {
                throw new Error(
                    `Status HTTP ${response.status}`
                );
            }


            const data =
                await response.json();


            temporaryErrors = 0;


            const job =
                data.job || data;


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


            if (
                status === "COMPLETED" ||
                status === "COMPLETE" ||
                status === "SUCCESS"
            ) {

                await showResult(job);

                return;
            }


            if (
                status === "FAILED" ||
                status === "ERROR"
            ) {

                throw new Error(
                    job.error ||
                    job.message ||
                    "Video processing failed."
                );
            }


        } catch (error) {

            temporaryErrors++;

            console.warn(
                "Status check failed:",
                error
            );


            if (temporaryErrors >= 10) {

                throw new Error(
                    "Unable to contact processing server."
                );
            }
        }


        await sleep(3000);
    }
}


/* =========================
   RESULT
========================= */

async function showResult(job) {

    setProgress(
        100,
        "Completed!"
    );


    showStatus(
        "✅ Your Burmese AI recap is ready!",
        "success"
    );


    let outputFile =
        job.output_file ||
        job.output_filename ||
        job.filename;


    if (!outputFile) {

        throw new Error(
            "Processing completed but output video was not found."
        );
    }


    outputFile =
        String(outputFile)
            .split("/")
            .pop();


    const videoURL =
        `${API_URL}/api/files/${encodeURIComponent(outputFile)}`;


    resultVideo.src = videoURL;
    resultVideo.load();


    downloadButton.href = videoURL;
    downloadButton.download = outputFile;


    if (job.recap_text) {

        recapText.textContent =
            job.recap_text;
    } else {

        recapText.textContent =
            "Burmese AI recap completed.";
    }


    resultSection.classList.remove(
        "hidden"
    );


    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}
