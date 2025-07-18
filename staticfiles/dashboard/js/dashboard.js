// Dashboard JavaScript Functionality

document.addEventListener("DOMContentLoaded", function () {
  // Initialize tooltips
  var tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Auto-hide alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert:not(.alert-permanent)");
  alerts.forEach((alert) => {
    setTimeout(() => {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // Sidebar active state management
  const currentPath = window.location.pathname;
  const sidebarLinks = document.querySelectorAll(".sidebar .nav-link");

  sidebarLinks.forEach((link) => {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });

  // Card hover effects
  const cards = document.querySelectorAll(".card");
  cards.forEach((card) => {
    if (!card.classList.contains("no-hover")) {
      card.addEventListener("mouseenter", function () {
        this.style.transform = "translateY(-2px)";
      });

      card.addEventListener("mouseleave", function () {
        this.style.transform = "translateY(0)";
      });
    }
  });

  // Loading state utility
  window.setLoading = function (element, isLoading = true) {
    if (isLoading) {
      element.disabled = true;
      element.classList.add("loading");
      const originalText = element.innerHTML;
      element.setAttribute("data-original-text", originalText);
      element.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    } else {
      element.disabled = false;
      element.classList.remove("loading");
      const originalText = element.getAttribute("data-original-text");
      if (originalText) {
        element.innerHTML = originalText;
      }
    }
  };

  // Utility function for showing notifications
  window.showNotification = function (message, type = "info") {
    const alertContainer =
      document.querySelector(".alert-container") ||
      document.querySelector("main");
    const alertId = "alert-" + Date.now();

    const alertHTML = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

    alertContainer.insertAdjacentHTML("afterbegin", alertHTML);

    // Auto-hide after 5 seconds
    setTimeout(() => {
      const alert = document.getElementById(alertId);
      if (alert) {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
      }
    }, 5000);
  };

  // Confirm dialogs for destructive actions
  const deleteButtons = document.querySelectorAll('[data-action="delete"]');
  deleteButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const message =
        this.getAttribute("data-confirm") ||
        "Are you sure you want to delete this item?";
      if (confirm(message)) {
        // Proceed with delete action
        console.log("Delete confirmed");
      }
    });
  });

  // Form validation helpers
  window.validateForm = function (formElement) {
    const requiredFields = formElement.querySelectorAll("[required]");
    let isValid = true;

    requiredFields.forEach((field) => {
      if (!field.value.trim()) {
        field.classList.add("is-invalid");
        isValid = false;
      } else {
        field.classList.remove("is-invalid");
      }
    });

    return isValid;
  };

  // Real-time form validation
  const forms = document.querySelectorAll("form");
  forms.forEach((form) => {
    const inputs = form.querySelectorAll("input, textarea, select");
    inputs.forEach((input) => {
      input.addEventListener("blur", function () {
        if (this.hasAttribute("required") && !this.value.trim()) {
          this.classList.add("is-invalid");
        } else {
          this.classList.remove("is-invalid");
        }
      });
    });
  });

  // Enhanced sidebar scrolling functionality
  const sidebar = document.querySelector(".sidebar-sticky");
  if (sidebar) {
    // Smooth scrolling to active item
    const activeLink = sidebar.querySelector(".nav-link.active");
    if (activeLink) {
      setTimeout(() => {
        activeLink.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }, 100);
    }

    // Improve scroll performance
    let isScrolling = false;
    sidebar.addEventListener("scroll", function () {
      if (!isScrolling) {
        window.requestAnimationFrame(function () {
          // Add scroll shadow effects
          const scrollTop = sidebar.scrollTop;
          const scrollHeight = sidebar.scrollHeight;
          const clientHeight = sidebar.clientHeight;

          if (scrollTop > 10) {
            sidebar.classList.add("scrolled-top");
          } else {
            sidebar.classList.remove("scrolled-top");
          }

          if (scrollTop < scrollHeight - clientHeight - 10) {
            sidebar.classList.add("scrolled-bottom");
          } else {
            sidebar.classList.remove("scrolled-bottom");
          }

          isScrolling = false;
        });
        isScrolling = true;
      }
    });
  }

  // Mobile sidebar functionality
  function initMobileSidebar() {
    const sidebar = document.getElementById("sidebar");
    const mobileToggle = document.querySelector(".mobile-toggle");

    if (sidebar && mobileToggle) {
      // Create backdrop
      const backdrop = document.createElement("div");
      backdrop.className = "sidebar-backdrop";
      document.body.appendChild(backdrop);

      // Toggle sidebar
      mobileToggle.addEventListener("click", function () {
        sidebar.classList.toggle("show");
        backdrop.classList.toggle("show");
        document.body.style.overflow = sidebar.classList.contains("show")
          ? "hidden"
          : "";
      });

      // Close on backdrop click
      backdrop.addEventListener("click", function () {
        sidebar.classList.remove("show");
        backdrop.classList.remove("show");
        document.body.style.overflow = "";
      });

      // Close on escape key
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && sidebar.classList.contains("show")) {
          sidebar.classList.remove("show");
          backdrop.classList.remove("show");
          document.body.style.overflow = "";
        }
      });
    }
  }

  // Initialize mobile sidebar
  initMobileSidebar();
});

// Utility functions available globally
window.DashboardUtils = {
  // Format file size
  formatFileSize: function (bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  },

  // Format date
  formatDate: function (date) {
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  },

  // Copy to clipboard
  copyToClipboard: function (text) {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        window.showNotification("Copied to clipboard!", "success");
      })
      .catch(() => {
        window.showNotification("Failed to copy to clipboard", "danger");
      });
  },

  // Debounce function
  debounce: function (func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },
};
