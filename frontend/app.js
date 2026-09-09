function monitorJob(jobId) {
    stopPolling();

    let retryCount = 0;

    checkJobStatus(jobId);

    statusTimer = setInterval(() => {
        checkJobStatus(jobId, retryCount);
    }, 3000);
}


async function checkJobStatus(jobId, retryCount = 0) {
    try {
        const response = await fetch(
            `${API_URL}/api/status/${jobId}`,
            {
                method: "GET",
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `Server returned ${response.status}`
            );
        }

        const data = await response.json();
        const job = data.job;

        setProgress(
            job.progress || 0,
            job.message || "AI is processing your video..."
        );

        if (job.status === "COMPLETED") {
            stopPolling();

            statusBox.textContent =
                "🎉 Recap completed successfully!";

            if (job.output_file) {
                showResult(
                    job.output_file,
                    job.recap_text
                );
            }

            return;
        }

        if (job.status === "FAILED") {
            stopPolling();

            showError(
                job.error ||
                "Video processing failed."
            );

            return;
        }

        // Processing is still running
        retryCount = 0;

    } catch (error) {
        console.warn(
            "Status connection temporarily unavailable:",
            error
        );

        retryCount++;

        // DO NOT stop polling.
        // Render Free can wake/restart temporarily.
        setProgress(
            Math.min(
                99,
                Math.max(
                    1,
                    retryCount
                )
            ),
            `⏳ Processing... reconnecting (${retryCount})`
        );

        statusBox.textContent =
            "🔄 Server connection temporarily unavailable — retrying...";

        // Keep polling instead of showing "Failed to fetch"
        if (retryCount >= 20) {
            statusBox.textContent =
                "⏳ Server is taking longer than expected. Processing continues...";
        }
    }
}
