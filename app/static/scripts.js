// Status stream
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

// Dropdown
var dropdown = document.querySelector('.dropdown');
dropdown.addEventListener('click', function(event) {
  event.stopPropagation();
  dropdown.classList.toggle('is-active');
});
document.addEventListener('click', function() {
  dropdown.classList.remove('is-active');
});

// API functions
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".api-action").forEach(link => {
    link.addEventListener("click", async (event) => {
      event.preventDefault();

      const url = link.getAttribute("href");
      const bodyData = link.getAttribute("data-body");
      const options = { method: "POST" };

      if (bodyData) {
        options.headers = { "Content-Type": "application/json" };
        options.body = bodyData;
      }

      try {
        const rsp = await fetch(url, options);
        const j = await rsp.json();

        if (j.filename) {
          const fileUrl = `/api/captures/${encodeURIComponent(j.filename)}`;

          try {
            const fileResponse = await fetch(fileUrl);
            const blob = await fileResponse.blob();

            const a = document.createElement("a");
            const fileDownloadUrl = URL.createObjectURL(blob);
            a.href = fileDownloadUrl;
            a.download = j.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(fileDownloadUrl); // Clean up the object URL
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