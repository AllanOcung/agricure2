// Dashboard Charts JavaScript

document.addEventListener("DOMContentLoaded", function () {
  // Sensor Trends Chart Data
  const sensorTrendData = {
    labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    datasets: [
      {
        label: "Humidity (%)",
        data: [65, 68, 72, 70, 75, 78, 72],
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59, 130, 246, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
      },
      {
        label: "Temperature (°C)",
        data: [25, 27, 24, 26, 23, 22, 25],
        borderColor: "#ef4444",
        backgroundColor: "rgba(239, 68, 68, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
      },
      {
        label: "Soil Moisture (%)",
        data: [45, 42, 38, 40, 44, 48, 46],
        borderColor: "#22c55e",
        backgroundColor: "rgba(34, 197, 94, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
      },
    ],
  };

  // Disease Frequency Chart Data
  const diseaseFrequencyData = {
    labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    datasets: [
      {
        label: "Diseases Detected",
        data: [12, 8, 15, 22, 18, 25],
        backgroundColor: "#059669",
        borderColor: "#059669",
        borderWidth: 1,
        borderRadius: 4,
        borderSkipped: false,
      },
    ],
  };

  // Chart Options
  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          usePointStyle: true,
          padding: 20,
          font: {
            size: 12,
          },
        },
      },
      tooltip: {
        mode: "index",
        intersect: false,
        backgroundColor: "rgba(0, 0, 0, 0.8)",
        titleColor: "white",
        bodyColor: "white",
        borderColor: "rgba(255, 255, 255, 0.1)",
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        grid: {
          display: true,
          color: "rgba(0, 0, 0, 0.1)",
        },
        ticks: {
          font: {
            size: 12,
          },
        },
      },
      y: {
        grid: {
          display: true,
          color: "rgba(0, 0, 0, 0.1)",
        },
        ticks: {
          font: {
            size: 12,
          },
        },
      },
    },
    interaction: {
      mode: "nearest",
      axis: "x",
      intersect: false,
    },
  };

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: "rgba(0, 0, 0, 0.8)",
        titleColor: "white",
        bodyColor: "white",
        borderColor: "rgba(255, 255, 255, 0.1)",
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 12,
          },
        },
      },
      y: {
        grid: {
          display: true,
          color: "rgba(0, 0, 0, 0.1)",
        },
        ticks: {
          font: {
            size: 12,
          },
        },
        beginAtZero: true,
      },
    },
  };

  // Initialize Sensor Trends Chart
  const sensorCtx = document.getElementById("sensorTrendsChart");
  if (sensorCtx) {
    new Chart(sensorCtx, {
      type: "line",
      data: sensorTrendData,
      options: lineChartOptions,
    });
  }

  // Initialize Disease Frequency Chart
  const diseaseCtx = document.getElementById("diseaseFrequencyChart");
  if (diseaseCtx) {
    new Chart(diseaseCtx, {
      type: "bar",
      data: diseaseFrequencyData,
      options: barChartOptions,
    });
  }

  // Add animation to cards on scroll
  const observerOptions = {
    threshold: 0.1,
    rootMargin: "0px 0px -100px 0px",
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = "1";
        entry.target.style.transform = "translateY(0)";
      }
    });
  }, observerOptions);

  // Observe all cards
  document.querySelectorAll(".card").forEach((card) => {
    card.style.opacity = "0";
    card.style.transform = "translateY(20px)";
    card.style.transition = "opacity 0.6s ease, transform 0.6s ease";
    observer.observe(card);
  });

  // Add click handlers for diagnosis items
  document.querySelectorAll(".btn-view").forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      // You can add navigation logic here
      console.log("View details clicked");
    });
  });

  // Add hover effects for device items
  document.querySelectorAll(".device-item").forEach((item) => {
    item.addEventListener("mouseenter", function () {
      this.style.transform = "translateY(-2px)";
      this.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.1)";
    });

    item.addEventListener("mouseleave", function () {
      this.style.transform = "translateY(0)";
      this.style.boxShadow = "none";
    });
  });

  // Add hover effects for diagnosis items
  document.querySelectorAll(".diagnosis-item").forEach((item) => {
    item.addEventListener("mouseenter", function () {
      this.style.transform = "translateY(-2px)";
      this.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.1)";
    });

    item.addEventListener("mouseleave", function () {
      this.style.transform = "translateY(0)";
      this.style.boxShadow = "none";
    });
  });

  // Add smooth transitions to all interactive elements
  const style = document.createElement("style");
  style.textContent = `
    .device-item, .diagnosis-item {
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .card {
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
  `;
  document.head.appendChild(style);

  // Real-time data simulation (optional)
  function simulateRealTimeData() {
    // Simulate device readings updates
    const deviceValues = document.querySelectorAll(".device-value");

    setInterval(() => {
      deviceValues.forEach((element, index) => {
        if (index === 0) {
          // Soil moisture
          const currentValue = parseInt(element.textContent);
          const newValue = Math.max(
            30,
            Math.min(50, currentValue + (Math.random() - 0.5) * 2)
          );
          element.textContent = Math.round(newValue) + "%";
        } else if (index === 1) {
          // Temperature
          const currentValue = parseInt(element.textContent);
          const newValue = Math.max(
            20,
            Math.min(35, currentValue + (Math.random() - 0.5) * 1)
          );
          element.textContent = Math.round(newValue) + "°C";
        } else if (index === 2) {
          // Humidity
          const currentValue = parseInt(element.textContent);
          const newValue = Math.max(
            50,
            Math.min(80, currentValue + (Math.random() - 0.5) * 2)
          );
          element.textContent = Math.round(newValue) + "%";
        }
      });
    }, 5000); // Update every 5 seconds
  }

  // Uncomment to enable real-time simulation
  // simulateRealTimeData();
});
