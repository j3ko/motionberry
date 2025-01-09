window.onload = function() {
  //<editor-fold desc="Changeable Configuration Block">

  // the following lines will be replaced by docker/configurator, when it runs in a docker-container
  // Fetch the JSON file
  fetch('openapi.json') // Replace with the path to your JSON file
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(spec => {
      // Initialize Swagger UI with the fetched spec
      const ui = SwaggerUIBundle({
        spec: spec, // Pass the loaded JSON spec here
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout"
      });
    })
    .catch(error => {
      console.error('Failed to load spec:', error);
    });

  //</editor-fold>
};
