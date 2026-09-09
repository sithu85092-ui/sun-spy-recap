const API_URL = "";

const CHUNK_SIZE =
    5 * 1024 * 1024;

let currentUploadId = null;
let currentJobId = null;
let statusTimer = null;


const $ = id =>
    document.getElementById(id);


const videoInput =
    $("videoInput");

const selectButton =
    $("selectButton");

const dropZone =
    $("dropZone");

const fileInfo =
    $("fileInfo");

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


selectButton.onclick = () => {

    videoInput.click();

};


videoInput.onchange = () => {

    const file =
        videoInput.files[0];

    if (file) {

        uploadVideo(file);

    }

};


dropZone.ondragover = event => {

    event.preventDefault();

    dropZone.classList.add(
        "dragover"
    );

};


dropZone.ondragleave = () => {

    dropZone.classList.remove(
        "dragover"
    );

};


dropZone.ondrop = event => {

    event.preventDefault();

    dropZone.classList.remove(
        "dragover"
    );

    const file =
        event.dataTransfer.files[0];

    if (
        file &&
        file.type.startsWith(
            "video/"
        )
    ) {

        uploadVideo(file);

    } else {

        showError(
            "Please select a valid video file."
        );

    }

};


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


        const init =
            await fetch(
                `${API_URL}/api/upload/init`,
                {
                    method: "POST",
                    body: initForm
                }
            );


        if (!init.ok) {

            throw new Error(
                await init.text()
            );

        }


        const initData =
            await init.json();


        currentUploadId =
            initData.upload_id;


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
                    `Chunk ${index + 1} failed: ${await response.text()}`
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


        const complete =
            await fetch(
                `${API_URL}/api/upload/complete`,
                {
                    method: "POST",
                    body: completeForm
                }
            );


        if (!complete.ok) {

            throw new Error(
                await complete.text()
            );

        }


        const completeData =
            await complete.json();


        statusBox.textContent =
            "🎬 Starting AI recap...";


        const recap =
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


        if (!recap.ok) {

            throw new Error(
                await recap.text()
            );

        }


        const recapData =
            await recap.json();


        currentJobId =
            recapData.job_id;


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
            2000
        );

}


async function checkJobStatus(
    jobId
) {

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
            job.message ||
            "Processing..."
        );


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

        }


        if (
            job.status ===
            "FAILED"
        ) {

            stopPolling();

            showError(
                job.error ||
                "Video processing failed."
            );

        }


    } catch (error) {

        stopPolling();

        showError(
            error.message
        );

    }

}


function showResult(
    path,
    text
) {

    const filename =
        path
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


function stopPolling() {

    if (statusTimer) {

        clearInterval(
            statusTimer
        );

    }

    statusTimer = null;

}


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
        `${value}%`;


    progressText.textContent =
        message ||
        "Processing...";

}


function showError(
    message
) {

    statusBox.classList.remove(
        "hidden"
    );


    statusBox.textContent =
        `❌ ${message}`;


    progressBar.style.width =
        "0%";


    progressPercent.textContent =
        "0%";


    progressText.textContent =
        "Processing stopped.";

}


function formatSize(
    bytes
) {

    if (bytes < 1024) {

        return `${bytes} B`;

    }


    if (
        bytes <
        1024 ** 2
    ) {

        return `${(
            bytes / 1024
        ).toFixed(2)} KB`;

    }


    if (
        bytes <
        1024 ** 3
    ) {

        return `${(
            bytes / 1024 ** 2
        ).toFixed(2)} MB`;

    }


    return `${(
        bytes / 1024 ** 3
    ).toFixed(2)} GB`;

}
