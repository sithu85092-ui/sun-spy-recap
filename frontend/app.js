const API_URL = "";

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
            showFile(file);
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

            videoInput.files = event.dataTransfer.files;

            showFile(file);

        }

    }
);


function showFile(file) {

    const sizeMB =
        (file.size / 1024 / 1024).toFixed(2);

    fileInfo.classList.remove("hidden");

    fileInfo.textContent =
        `Selected: ${file.name} • ${sizeMB} MB`;

    statusBox.classList.remove("hidden");

    statusBox.textContent =
        "Video selected. Upload engine will be connected next.";

}
