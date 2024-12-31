const eventSource = new EventSource("/api/status_stream");

eventSource.onmessage = function (event) {
  const data = JSON.parse(event.data);

function toggleStatus(parentSelector, isActive) {
  const parentElements = document.querySelectorAll(parentSelector);

  parentElements.forEach((parentElement) => {
    const elementOn = parentElement.querySelector(".on");
    const elementOff = parentElement.querySelector(".off");

    if (isActive) {
      if (elementOn) elementOn.classList.add("active");
      if (elementOff) elementOff.classList.remove("active");
    } else {
      if (elementOn) elementOn.classList.remove("active");
      if (elementOff) elementOff.classList.add("active");
    }
  });
}

  toggleStatus(".recording-status", data.is_recording);
  toggleStatus(".motion-detection-status", data.is_motion_detecting);
};

eventSource.onerror = function() {
  console.error("Error connecting to the status stream.");
};

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".api-action").forEach(link => {
    link.addEventListener("click", async (event) => {
      event.preventDefault();

      const url = link.getAttribute("href");

      try {
        const rsp = await fetch(url, { method: "POST" });
        const j = await rsp.json();

        if (j.filename) {
          const fileUrl = `/api/captures/${encodeURIComponent(j.filename)}`;

          try {
            const fileResponse = await fetch(fileUrl);
            const blob = await fileResponse.blob();

            // Create a temporary anchor element for download
            const a = document.createElement("a");
            const url = URL.createObjectURL(blob);
            a.href = url;
            a.download = j.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url); // Clean up the object URL
          } catch (error) {
            console.error("Error downloading the file:", error);
          }
        }

      } catch (error) {
        console.error("API action failed:", error);
      }
    });
  });
});