const eventSource = new EventSource("/api/status_stream");

eventSource.onmessage = function (event) {
  const data = JSON.parse(event.data);

  function toggleStatus(selector, isActive) {
    const elementOn = document.querySelector(`${selector} > .on`);
    const elementOff = document.querySelector(`${selector} > .off`);

    if (isActive) {
      elementOn.classList.add("active");
      elementOff.classList.remove("active");
    } else {
      elementOn.classList.remove("active");
      elementOff.classList.add("active");
    }
  }

  toggleStatus(".camera-status", data.is_camera_running);
  toggleStatus(".recording-status", data.is_recording);
  toggleStatus(".motion-detection-status", data.is_motion_detecting);
};

eventSource.onerror = function() {
  console.error("Error connecting to the status stream.");
};

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".api-action").forEach(link => {
    link.addEventListener("click", (event) => {
      event.preventDefault();

      const url = link.getAttribute("href");
      fetch(url, { method: "POST" })
        .catch(error => console.error("API action failed:", error));
    });
  });
});