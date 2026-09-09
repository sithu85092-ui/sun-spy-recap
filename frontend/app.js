const API_URL = "";

const CHUNK_SIZE = 5 * 1024 * 1024; // 5 MB

const videoInput = document.getElementById("videoInput");
const selectButton = document.getElementById("selectButton");
const dropZone = document.getElementById("dropZone");

const fileInfo = document.getElementById("fileInfo");
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


selectButton.addEventListener(
    "click",
    () => videoInput.click()
);


videoInput.addEventListener(
    "change",
    () => {

        const file = videoInput.files[0];

        if (file) {
            uploadVideo(file);
        }

    }
);


dropZone.addEventListener(
    "dragover",
    (event) => {

        event.preventDefault();
        dropZone.classList.add("dragover");

    }
);


dropZone.addEventListener(
    "dragleave",
    () => {

        dropZone.classList.remove("dragover");

    }
);


dropZone.addEventListener(
    "drop",
    (event) => {

        event.preventDefault();

        dropZone.classList.remove("dragover");

        const file = event.dataTransfer.files[0];

        if (file && file.type.startsWith("video/")) {
            uploadVideo(file);
        }

    }
);


async function uploadVideo(file) {

    try {

        fileInfo.classList.remove("hidden");

        fileInfo.textContent =
            `Selected: ${file.name} • ${formatSize(file.size)}`;

        progressContainer.classList.remove("hidden");

        statusBox.classList.remove("hidden");

        resultSection.classList.add("hidden");

        setProgress(
            0,
            "Starting upload..."
        );


        // 1. Initialize upload

        const initData = new FormData();

        initData.append(
            "filename",
            file.name
        );

        initData.append(
            "file_size",
            file.size
        );


        const initResponse =
            await fetch(
                `${API_URL}/api/upload/init`,
                {
                    method: "POST",
                    body: initData
                }
            );


        if (!initResponse.ok) {
            throw new Error(
                await initResponse.text()
            );
        }


        const upload =
            await initResponse.json();

        const uploadId =
            upload.upload_id;


        // 2. Upload chunks

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


            const formData =
                new FormData();

            formData.append(
                "upload_id",
                uploadId
            );

            formData.append(
                "chunk_index",
                index
            );

            formData.append(
                "chunk",
                chunk,
                file.name
            );


            const response =
                await fetch(
                    `${API_URL}/api/upload/chunk`,
                    {
                        method: "POST",
                        body: formData
                    }
                );


            if (!response.ok) {
                throw new Error(
                    await response.text()
                );
            }


            const progress =
                Math.round(
                    ((index + 1) /
                        totalChunks) * 100
                );


            setProgress(
                progress,
                `Uploading chunk ${index + 1} / ${totalChunks}`
            );

        }


        // 3. Complete upload

        setProgress(
            100,
            "Finishing upload..."
        );


        const completeData =
            new FormData();

        completeData.append(
            "upload_id",
            uploadId
        );

        completeData.append(
            "filename",
            file.name
        );

        completeData.append(
            "total_chunks",
            totalChunks
        );


        const completeResponse =
            await fetch(
                `${API_URL}/api/upload/complete`,
                {
                    method: "POST",
                    body: completeData
                }
            );


        if (!completeResponse.ok) {
            throw new Error(
                await completeResponse.text()
            );
        }


        const completed =
            await completeResponse.json();


        statusBox.textContent =
            "✅ Upload completed successfully. Starting recap...";


        // 4. Create recap job

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
                            completed.upload_id,

                        filename:
                            completed.filename
                    })
                }
            );


        if (!recapResponse.ok) {
            throw new Error(
                await recapResponse.text()
            );
        }


        const recap =
            await recapResponse.json();


        statusBox.textContent =
            "🎬 Recap processing started...";


        // 5. Monitor job

        monitorJob(
            recap.job_id
        );


    } catch (error) {

        console.error(error);

        statusBox.textContent =
            `❌ Error: ${error.message}`;

    }

}


async function monitorJob(jobId) {

    const timer =
        setInterval(
            async () => {

                try {

                    const response =
                        await fetch(
                            `${API_URL}/api/status/${jobId}`
                        );


                    if (!response.ok) {
                        throw new Error(
                            "Unable to read job status"
                        );
                    }


                    const data =
                        await response.json();

                    const job =
                        data.job;


                    setProgress(
                        job.progress,
                        job.message
                    );


                    if (
                        job.status ===
                        "COMPLETED"
                    ) {

                        clearInterval(timer);

                        statusBox.textContent =
                            "🎉 Recap completed!";

                        showResult(
                            job.output_file
                        );

                    }


                    if (
                        job.status ===
                        "FAILED"
                    ) {

                        clearInterval(timer);

                        statusBox.textContent =
                            `❌ ${job.error || "Processing failed"}`;

                    }


                } catch (error) {

                    clearInterval(timer);

                    statusBox.textContent =
                        `❌ ${error.message}`;

                }

            },
            2000
        );

}


function showResult(path) {

    resultSection.classList.remove(
        "hidden"
    );

    /*
     * Backend currently returns a server path.
     * The public download/stream endpoint
     * will be added in the next phase.
     */

    resultVideo.removeAttribute(
        "src"
    );

    resultVideo.load();

}


function setProgress(
    percent,
    message
) {

    progressBar.style.width =
        `${percent}%`;

    progressPercent.textContent =
        `${percent}%`;

    progressText.textContent =
        message;

}


function formatSize(bytes) {

    const mb =
        bytes / 1024 / 1024;

    if (mb < 1024) {
        return `${mb.toFixed(2)} MB`;
    }

    return `${(
        mb / 1024
    ).toFixed(2)} GB`;

}
