const API_URL = "";

const CHUNK_SIZE = 5 * 1024 * 1024;

let currentUploadId = null;
let currentJobId = null;
let currentFile = null;
let statusTimer = null;


const videoInput =
    document.getElementById("videoInput");

const selectButton =
    document.getElementById("selectButton");

const dropZone =
    document.getElementById("dropZone");

const fileInfo =
    document.getElementById("fileInfo");

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


/*
|--------------------------------------------------------------------------
| Select Video
|--------------------------------------------------------------------------
*/

selectButton.addEventListener(
    "click",
    () => {
        videoInput.click();
    }
);


videoInput.addEventListener(
    "change",
    () => {

        const file =
            videoInput.files[0];

        if (file) {
            uploadVideo(file);
        }
    }
);


/*
|--------------------------------------------------------------------------
| Drag & Drop
|--------------------------------------------------------------------------
*/

dropZone.addEventListener(
    "dragover",
    (event) => {

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
    (event) => {

        event.preventDefault();

        dropZone.classList.remove(
            "dragover"
        );

        const file =
            event.dataTransfer.files[0];

        if (
            file &&
            file.type.startsWith("video/")
        ) {
            uploadVideo(file);
        } else {
            showError(
                "Please select a valid video file."
            );
        }
    }
);


/*
|--------------------------------------------------------------------------
| Upload Video
|--------------------------------------------------------------------------
*/

async function uploadVideo(file) {

    try {

        currentFile = file;

        resultSection.classList.add(
            "hidden"
        );

        resultVideo.removeAttribute(
            "src"
        );

        fileInfo.classList.remove(
            "hidden"
        );

        fileInfo.textContent =
            `Selected: ${file.name} • ${formatSize(file.size)}`;

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


        /*
        |--------------------------------------------------------------------------
        | 1. Initialize Upload
        |--------------------------------------------------------------------------
        */

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

            const errorText =
                await initResponse.text();

            throw new Error(
                `Upload initialization failed: ${errorText}`
            );
        }


        const initData =
            await initResponse.json();


        currentUploadId =
            initData.upload_id;


        /*
        |--------------------------------------------------------------------------
        | 2. Upload Chunks
        |--------------------------------------------------------------------------
        */

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


            const chunkForm =
                new FormData();

            chunkForm.append(
                "upload_id",
                currentUploadId
            );

            chunkForm.append(
                "chunk_index",
                index
            );

            chunkForm.append(
                "chunk",
                chunk,
                file.name
            );


            const chunkResponse =
                await fetch(
                    `${API_URL}/api/upload/chunk`,
                    {
                        method: "POST",
                        body: chunkForm
                    }
                );


            if (!chunkResponse.ok) {

                const errorText =
                    await chunkResponse.text();

                throw new Error(
                    `Chunk ${index + 1} failed: ${errorText}`
                );
            }


            const percent =
                Math.round(
                    ((index + 1) /
                        totalChunks) *
                    100
                );


            setProgress(
                percent,
                `Uploading ${index + 1} / ${totalChunks}`
            );
        }


        /*
        |--------------------------------------------------------------------------
        | 3. Complete Upload
        |--------------------------------------------------------------------------
        */

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

            const errorText =
                await completeResponse.text();

            throw new Error(
                `Upload completion failed: ${errorText}`
            );
        }


        const completeData =
            await completeResponse.json();


        statusBox.textContent =
            "✅ Upload completed. Starting recap...";


        /*
        |--------------------------------------------------------------------------
        | 4. Create Recap Job
        |--------------------------------------------------------------------------
        */

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

            const errorText =
                await recapResponse.text();

            throw new Error(
                `Recap creation failed: ${errorText}`
            );
        }


        const recapData =
            await recapResponse.json();


        currentJobId =
            recapData.job_id;


        statusBox.textContent =
            "🎬 AI recap processing started...";


        /*
        |--------------------------------------------------------------------------
        | 5. Monitor Job
        |--------------------------------------------------------------------------
        */

        monitorJob(
            currentJobId
        );


    } catch (error) {

        console.error(
            "SUN SPY RECAP ERROR:",
            error
        );

        showError(
            error.message
        );
    }
}


/*
|--------------------------------------------------------------------------
| Monitor Processing Job
|--------------------------------------------------------------------------
*/

function monitorJob(jobId) {

    if (statusTimer) {
        clearInterval(statusTimer);
    }


    checkJobStatus(jobId);


    statusTimer =
        setInterval(
            () => {
                checkJobStatus(jobId);
            },
            2000
        );
}


async function checkJobStatus(jobId) {

    try {

        const response =
            await fetch(
                `${API_URL}/api/status/${jobId}`
            );


        if (!response.ok) {

            throw new Error(
                "Unable to get processing status."
            );
        }


        const data =
            await response.json();

        const job =
            data.job;


        setProgress(
            job.progress || 0,
            job.message || "Processing..."
        );


        /*
        |--------------------------------------------------------------------------
        | Completed
        |--------------------------------------------------------------------------
        */

        if (
            job.status ===
            "COMPLETED"
        ) {

            clearInterval(
                statusTimer
            );

            statusTimer = null;


            statusBox.textContent =
                "🎉 Recap completed successfully!";


            if (job.output_file) {

                showResult(
                    job.output_file
                );
            }

            return;
        }


        /*
        |--------------------------------------------------------------------------
        | Failed
        |--------------------------------------------------------------------------
        */

        if (
            job.status ===
            "FAILED"
        ) {

            clearInterval(
                statusTimer
            );

            statusTimer = null;


            showError(
                job.error ||
                "Video processing failed."
            );

            return;
        }


    } catch (error) {

        console.error(
            "Status error:",
            error
        );

        clearInterval(
            statusTimer
        );

        statusTimer = null;

        showError(
            error.message
        );
    }
}


/*
|--------------------------------------------------------------------------
| Show Result Video
|--------------------------------------------------------------------------
*/

function showResult(path) {

    resultSection.classList.remove(
        "hidden"
    );


    const filename =
        path
            .split("/")
            .pop()
            .split("\\")
            .pop();


    const videoURL =
        `${API_URL}/api/files/${encodeURIComponent(filename)}`;


    resultVideo.src =
        videoURL;


    resultVideo.load();


    resultVideo.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


/*
|--------------------------------------------------------------------------
| Progress
|--------------------------------------------------------------------------
*/

function setProgress(
    percent,
    message
) {

    const safePercent =
        Math.max(
            0,
            Math.min(
                100,
                Number(percent) || 0
            )
        );


    progressBar.style.width =
        `${safePercent}%`;


    progressPercent.textContent =
        `${safePercent}%`;


    progressText.textContent =
        message || "Processing...";
}


/*
|--------------------------------------------------------------------------
| Error
|--------------------------------------------------------------------------
*/

function showError(message) {

    statusBox.classList.remove(
        "hidden"
    );


    statusBox.textContent =
        `❌ ${message}`;


    progressText.textContent =
        "Processing stopped.";


    progressBar.style.width =
        "0%";


    progressPercent.textContent =
        "0%";
}


/*
|--------------------------------------------------------------------------
| File Size
|--------------------------------------------------------------------------
*/

function formatSize(bytes) {

    if (bytes < 1024) {
        return `${bytes} B`;
    }


    if (bytes < 1024 * 1024) {

        return `${(
            bytes / 1024
        ).toFixed(2)} KB`;
    }


    if (
        bytes <
        1024 * 1024 * 1024
    ) {

        return `${(
            bytes /
            1024 /
            1024
        ).toFixed(2)} MB`;
    }


    return `${(
        bytes /
        1024 /
        1024 /
        1024
    ).toFixed(2)} GB`;
}
