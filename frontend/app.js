const API_URL = "https://sun-spy-recap.onrender.com";

const CHUNK_SIZE = 5 * 1024 * 1024;

let currentUploadId = null;
let currentJobId = null;
let statusTimer = null;
let previewUrl = null;

const $ = id => document.getElementById(id);

const videoInput = $("videoInput");
const selectButton = $("selectButton");
const dropZone = $("dropZone");

const fileInfo = $("fileInfo");

const inputPreviewContainer =
    $("inputPreviewContainer");

const inputPreview =
    $("inputPreview");

const progressContainer =
    $("progressContainer");

const progressBar =
    $("progressBar");

const progressPercent =
    $("progressPercent");

const progressText =
    $("progressText");

const statusBox =
    $("statusBox");

const resultSection =
    $("resultSection");

const resultVideo =
    $("resultVideo");

const downloadButton =
    $("downloadButton");

const recapText =
    $("recapText");


// ================================
// FILE SELECT
// ================================

videoInput.addEventListener(
    "change",
    () => {

        const file =
            videoInput.files &&
            videoInput.files[0];

        if (!file) return;

        if (
            !file.type ||
            !file.type.startsWith("video/")
        ) {

            showError(
                "Please select a valid video file."
            );

            return;
        }

        uploadVideo(file);
    }
);


// ================================
// DRAG & DROP
// ================================

dropZone.addEventListener(
    "dragover",
    event => {

        event.preventDefault();

        dropZone.classList.add(
            "dragover"
        );
    }
);

dropZone.addEventListener(
    "dragleave",
    () => {

        dropZone.classList.remove(
            "dragover"
        );
    }
);

dropZone.addEventListener(
    "drop",
    event => {

        event.preventDefault();

        dropZone.classList.remove(
            "dragover"
        );

        const file =
            event.dataTransfer.files &&
            event.dataTransfer.files[0];

        if (!file) return;

        if (
            !file.type ||
            !file.type.startsWith("video/")
        ) {

            showError(
                "Please select a valid video file."
            );

            return;
        }

        uploadVideo(file);
    }
);


// ================================
// UPLOAD VIDEO
// ================================

async function uploadVideo(file) {

    try {

        stopPolling();

        resultSection.classList.add(
            "hidden"
        );

        resultVideo.removeAttribute(
            "src"
        );

        recapText.textContent = "";

        // ----------------------------
        // Show selected file
        // ----------------------------

        fileInfo.classList.remove(
            "hidden"
        );

        fileInfo.textContent =
            `Selected: ${file.name} • ${formatSize(file.size)}`;


        // ----------------------------
        // Local video preview
        // ----------------------------

        if (previewUrl) {

            URL.revokeObjectURL(
                previewUrl
            );
        }

        previewUrl =
            URL.createObjectURL(file);

        inputPreview.src =
            previewUrl;

        inputPreviewContainer.classList.remove(
            "hidden"
        );

        inputPreview.load();


        // ----------------------------
        // Progress
        // ----------------------------

        progressContainer.classList.remove(
            "hidden"
        );

        statusBox.classList.remove(
            "hidden"
        );

        setProgress(
            0,
            "Preparing upload..."
        );


        // ============================
        // 1. INIT UPLOAD
        // ============================

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


        const initResponse =
            await fetch(
                `${API_URL}/api/upload/init`,
                {
                    method: "POST",
                    body: initForm
                }
            );


        if (!initResponse.ok) {

            throw new Error(
                await getResponseError(
                    initResponse
                )
            );
        }


        const initData =
            await initResponse.json();


        if (
            !initData.success ||
            !initData.upload_id
        ) {

            throw new Error(
                "Upload initialization failed."
            );
        }


        currentUploadId =
            initData.upload_id;


        // ============================
        // 2. CHUNK UPLOAD
        // ============================

        const totalChunks =
            Math.ceil(
                file.size /
                CHUNK_SIZE
            );


        for (
            let index = 0;
            index < totalChunks;
            index++
        ) {

            const start =
                index *
                CHUNK_SIZE;

            const end =
                Math.min(
                    start +
                    CHUNK_SIZE,
                    file.size
                );


            const chunk =
                file.slice(
                    start,
                    end
                );


            const form =
                new FormData();


            form.append(
                "upload_id",
                currentUploadId
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


            let uploaded = false;


            // Small retry for temporary network errors
            for (
                let attempt = 1;
                attempt <= 3;
                attempt++
            ) {

                try {

                    const response =
                        await fetch(
                            `${API_URL}/api/upload/chunk`,
                            {
                                method: "POST",
                                body: form
                            }
                        );


                    if (!response.ok) {

                        throw new Error(
                            await getResponseError(
                                response
                            )
                        );
                    }


                    uploaded = true;

                    break;

                } catch (error) {

                    if (
                        attempt === 3
                    ) {

                        throw error;
                    }


                    setProgress(
                        Math.round(
                            (index /
                                totalChunks) *
                            100
                        ),
                        `Retrying chunk ${index + 1}...`
                    );


                    await sleep(
                        1500
                    );
                }
            }


            if (!uploaded) {

                throw new Error(
                    `Chunk ${index + 1} failed.`
                );
            }


            setProgress(
                Math.round(
                    ((index + 1) /
                        totalChunks) *
                    100
                ),
                `Uploading ${index + 1} / ${totalChunks}`
            );
        }


        // ============================
        // 3. COMPLETE UPLOAD
        // ============================

        setProgress(
            100,
            "Finalizing upload..."
        );


        const completeForm =
            new FormData();


        completeForm.append(
            "upload_id",
            currentUploadId
        );

        completeForm.append(
            "filename",
            file.name
        );

        completeForm.append(
            "total_chunks",
            totalChunks
        );


        const completeResponse =
            await fetch(
                `${API_URL}/api/upload/complete`,
                {
                    method: "POST",
                    body: completeForm
                }
            );


        if (!completeResponse.ok) {

            throw new Error(
                await getResponseError(
                    completeResponse
                )
            );
        }


        const completeData =
            await completeResponse.json();


        if (
            !completeData.success ||
            !completeData.filename
        ) {

            throw new Error(
                "Upload finalization failed."
            );
        }


        // ============================
        // 4. START AI RECAP
        // ============================

        statusBox.textContent =
            "🎬 Starting AI recap...";


        setProgress(
            0,
            "AI is analyzing your video..."
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

                        upload_id:
                            completeData.upload_id,

                        filename:
                            completeData.filename
                    })
                }
            );


        if (!recapResponse.ok) {

            throw new Error(
                await getResponseError(
                    recapResponse
                )
            );
        }


        const recapData =
            await recapResponse.json();


        if (
            !recapData.success ||
            !recapData.job_id
        ) {

            throw new Error(
                "AI recap could not be started."
            );
        }


        currentJobId =
            recapData.job_id;


        // ============================
        // 5. MONITOR JOB
        // ============================

        monitorJob(
            currentJobId
        );


    } catch (error) {

        console.error(
            "SUN SPY RECAP:",
            error
        );


        showError(
            error.message ||
            "Something went wrong."
        );
    }
}


// ================================
// JOB MONITOR
// ================================

function monitorJob(jobId) {

    stopPolling();

    checkJobStatus(
        jobId
    );


    statusTimer =
        setInterval(
            () => {

                checkJobStatus(
                    jobId
                );

            },
            3000
        );
}


// ================================
// CHECK STATUS
// ================================

async function checkJobStatus(
    jobId
) {

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
                "Unable to get processing status."
            );
        }


        const data =
            await response.json();


        if (
            !data.success ||
            !data.job
        ) {

            throw new Error(
                "Invalid processing status."
            );
        }


        const job =
            data.job;


        setProgress(
            job.progress || 0,
            job.message ||
            "Processing..."
        );


        // ----------------------------
        // COMPLETED
        // ----------------------------

        if (
            job.status ===
            "COMPLETED"
        ) {

            stopPolling();

            statusBox.textContent =
                "🎉 Recap completed successfully!";


            if (
                job.output_file
            ) {

                showResult(
                    job.output_file,
                    job.recap_text
                );
            }

            return;
        }


        // ----------------------------
        // FAILED
        // ----------------------------

        if (
            job.status ===
            "FAILED"
        ) {

            stopPolling();

            showError(
                job.error ||
                "Video processing failed."
            );

            return;
        }

    } catch (error) {

        // Do NOT immediately stop polling.
        // Render may temporarily wake up.

        console.warn(
            "Status check failed:",
            error
        );

        statusBox.textContent =
            "⏳ Server is waking up... retrying...";

    }
}


// ================================
// SHOW RESULT
// ================================

function showResult(
    path,
    text
) {

    const filename =
        String(path)
            .split("/")
            .pop()
            .split("\\")
            .pop();


    const url =
        `${API_URL}/api/files/${encodeURIComponent(filename)}`;


    resultSection.classList.remove(
        "hidden"
    );


    resultVideo.src =
        url;


    downloadButton.href =
        url;


    recapText.textContent =
        text || "";


    resultVideo.load();


    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


// ================================
// STOP POLLING
// ================================

function stopPolling() {

    if (statusTimer) {

        clearInterval(
            statusTimer
        );
    }

    statusTimer = null;
}


// ================================
// PROGRESS
// ================================

function setProgress(
    percent,
    message
) {

    const value =
        Math.max(
            0,
            Math.min(
                100,
                Number(percent) || 0
            )
        );


    progressBar.style.width =
        `${value}%`;


    progressPercent.textContent =
        `${Math.round(value)}%`;


    progressText.textContent =
        message ||
        "Processing...";
}


// ================================
// ERROR
// ================================

function showError(
    message
) {

    statusBox.classList.remove(
        "hidden"
    );


    statusBox.textContent =
        `❌ ${message}`;


    progressText.textContent =
        "Processing stopped.";
}


// ================================
// RESPONSE ERROR
// ================================

async function getResponseError(
    response
) {

    try {

        const text =
            await response.text();

        if (text) {

            return text;
        }

    } catch (error) {

        console.warn(
            error
        );
    }


    return `Server error (${response.status})`;
}


// ================================
// SLEEP
// ================================

function sleep(
    milliseconds
) {

    return new Promise(
        resolve =>
            setTimeout(
                resolve,
                milliseconds
            )
    );
}


// ================================
// FILE SIZE
// ================================

function formatSize(
    bytes
) {

    if (
        bytes < 1024
    ) {

        return `${bytes} B`;
    }


    if (
        bytes < 1024 ** 2
    ) {

        return `${(
            bytes /
            1024
        ).toFixed(2)} KB`;
    }


    if (
        bytes < 1024 ** 3
    ) {

        return `${(
            bytes /
            1024 ** 2
        ).toFixed(2)} MB`;
    }


    return `${(
        bytes /
        1024 ** 3
    ).toFixed(2)} GB`;
}
