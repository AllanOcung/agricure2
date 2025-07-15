// Admin Dashboard JavaScript
document.addEventListener("DOMContentLoaded", function () {
  // Initialize admin dashboard
  initializeAdminDashboard();

  // Auto-refresh system status
  setInterval(updateSystemStatus, 30000); // Every 30 seconds

  // Auto-refresh stats
  setInterval(updateStats, 60000); // Every minute
});

function initializeAdminDashboard() {
  // Update initial stats
  updateStats();
  updateSystemStatus();

  // Initialize sidebar toggle for mobile
  initializeSidebarToggle();

  // Initialize notification system
  initializeNotifications();
}

function updateStats() {
  fetch("/dashboard/admin/api/stats/")
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        console.error("Error fetching stats:", data.error);
        return;
      }

      // Update stat counters
      updateElement("model-count", data.total_models || 0);
      updateElement("diagnosis-count", data.total_diagnoses || 0);
      updateElement("dataset-size", data.dataset_size || 0);
      updateElement("user-count", data.total_users || 0);
    })
    .catch((error) => {
      console.error("Error updating stats:", error);
    });
}

function updateSystemStatus() {
  fetch("/dashboard/admin/api/system-metrics/")
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        console.error("Error fetching system status:", data.error);
        return;
      }

      // Update system status indicator
      const statusElement = document.getElementById("system-status");
      const statusTextElement = document.getElementById("system-status-text");

      if (statusElement && statusTextElement) {
        if (data.disk_usage > 90) {
          statusElement.className = "fas fa-circle text-danger";
          statusTextElement.textContent = "System Warning";
        } else if (data.disk_usage > 80) {
          statusElement.className = "fas fa-circle text-warning";
          statusTextElement.textContent = "System Caution";
        } else {
          statusElement.className = "fas fa-circle text-success";
          statusTextElement.textContent = "System Online";
        }
      }
    })
    .catch((error) => {
      console.error("Error updating system status:", error);

      // Show error state
      const statusElement = document.getElementById("system-status");
      const statusTextElement = document.getElementById("system-status-text");

      if (statusElement && statusTextElement) {
        statusElement.className = "fas fa-circle text-danger";
        statusTextElement.textContent = "System Error";
      }
    });
}

function initializeSidebarToggle() {
  const sidebarToggle = document.querySelector(".navbar-toggler");
  const sidebar = document.getElementById("admin-sidebar");

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("show");
    });
  }
}

function initializeNotifications() {
  // Check for training status updates
  setInterval(checkTrainingStatus, 10000); // Every 10 seconds
}

function checkTrainingStatus() {
  fetch("/dashboard/admin/api/training-status/")
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        console.error("Error checking training status:", data.error);
        return;
      }

      const notificationCount = document.getElementById("notification-count");

      if (data.status === "training" && notificationCount) {
        notificationCount.textContent = "1";
        notificationCount.style.display = "inline";

        // Update notification dropdown
        updateTrainingNotification(data);
      } else if (notificationCount) {
        notificationCount.textContent = "0";
        notificationCount.style.display = "none";
      }
    })
    .catch((error) => {
      console.error("Error checking training status:", error);
    });
}

function updateTrainingNotification(data) {
  const notificationDropdown = document.querySelector(".notification-dropdown");

  if (notificationDropdown) {
    const notificationHTML = `
            <li><h6 class="dropdown-header">Training in Progress</h6></li>
            <li><hr class="dropdown-divider"></li>
            <li>
                <a class="dropdown-item" href="/dashboard/admin/models/">
                    <div class="notification-item">
                        <i class="fas fa-brain text-info"></i>
                        <div>
                            <strong>Model Training</strong>
                            <small class="text-muted">Version: ${data.model_version}</small>
                        </div>
                    </div>
                </a>
            </li>
        `;

    notificationDropdown.innerHTML = notificationHTML;
  }
}

function updateElement(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

// Training management functions
function startTraining(form) {
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;

  submitBtn.disabled = true;
  submitBtn.innerHTML =
    '<i class="fas fa-spinner fa-spin"></i> Starting Training...';

  // Reset button after 5 seconds
  setTimeout(() => {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
  }, 5000);

  return true;
}

function confirmModelDeletion(modelName) {
  return confirm(
    `Are you sure you want to delete model "${modelName}"? This action cannot be undone.`
  );
}

function confirmModelActivation(modelName) {
  return confirm(
    `Are you sure you want to activate model "${modelName}"? This will deactivate the current active model.`
  );
}

// Health check functions
function runHealthCheck() {
  const healthCheckBtn = document.getElementById("health-check-btn");
  const healthResults = document.getElementById("health-results");

  if (healthCheckBtn) {
    healthCheckBtn.disabled = true;
    healthCheckBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> Running Checks...';
  }

  fetch("/dashboard/admin/health/check/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (healthResults) {
        displayHealthResults(data, healthResults);
      }
    })
    .catch((error) => {
      console.error("Error running health check:", error);
      if (healthResults) {
        healthResults.innerHTML =
          '<div class="alert alert-danger">Error running health check</div>';
      }
    })
    .finally(() => {
      if (healthCheckBtn) {
        healthCheckBtn.disabled = false;
        healthCheckBtn.innerHTML =
          '<i class="fas fa-stethoscope"></i> Run Health Check';
      }
    });
}

function displayHealthResults(data, container) {
  if (!data.success) {
    container.innerHTML = `<div class="alert alert-danger">Health check failed: ${data.error}</div>`;
    return;
  }

  let html = '<div class="health-results">';

  for (const [checkName, result] of Object.entries(data.checks)) {
    const statusClass =
      result.status === "healthy"
        ? "success"
        : result.status === "warning"
        ? "warning"
        : "danger";
    const statusIcon =
      result.status === "healthy"
        ? "check-circle"
        : result.status === "warning"
        ? "exclamation-triangle"
        : "times-circle";

    html += `
            <div class="alert alert-${statusClass}">
                <i class="fas fa-${statusIcon}"></i>
                <strong>${checkName
                  .replace("_", " ")
                  .toUpperCase()}</strong>: ${result.details}
            </div>
        `;
  }

  html += "</div>";
  container.innerHTML = html;
}

function getCsrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
}

// Export functions for use in templates
window.adminDashboard = {
  startTraining,
  confirmModelDeletion,
  confirmModelActivation,
  runHealthCheck,
  updateStats,
  updateSystemStatus,
};
