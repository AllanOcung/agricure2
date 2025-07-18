document.addEventListener("DOMContentLoaded", function () {
  // Get all navigation links
  const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');
  const sections = document.querySelectorAll("section[id], div[id]");
  let isScrolling = false;

  // Function to update active link
  function setActiveLink(activeLink) {
    navLinks.forEach((link) => link.classList.remove("active"));
    if (activeLink) {
      activeLink.classList.add("active");
    }
  }

  // Smooth scroll functionality
  navLinks.forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      isScrolling = true;

      const targetId = this.getAttribute("href");
      const targetSection = document.querySelector(targetId);

      if (targetSection) {
        // Immediately update active link for instant feedback
        setActiveLink(this);

        // Get navbar height for offset
        const navbarHeight = document.querySelector(".navbar").offsetHeight;

        // Calculate position with offset
        const targetPosition = targetSection.offsetTop - navbarHeight - 20;

        // Smooth scroll to target
        window.scrollTo({
          top: targetPosition,
          behavior: "smooth",
        });

        // Reset scrolling flag after animation completes
        setTimeout(() => {
          isScrolling = false;
        }, 1000);
      }
    });
  });

  // Active link highlighting on scroll (only when not manually scrolling)
  function updateActiveLink() {
    if (isScrolling) return; // Don't update during manual scroll

    const navbarHeight = document.querySelector(".navbar").offsetHeight;
    const scrollPosition = window.scrollY + navbarHeight + 100;

    let activeLink = null;

    sections.forEach((section) => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;
      const sectionId = section.getAttribute("id");

      if (
        scrollPosition >= sectionTop &&
        scrollPosition < sectionTop + sectionHeight
      ) {
        activeLink = document.querySelector(
          `.nav-links a[href="#${sectionId}"]`
        );
      }
    });

    // Handle edge case: if at the very top of the page, activate home link
    if (window.scrollY === 0) {
      activeLink = document.querySelector('.nav-links a[href="#home"]');
    }

    setActiveLink(activeLink);
  }

  // Use throttled scroll event for better performance
  let ticking = false;
  function handleScroll() {
    if (!ticking) {
      requestAnimationFrame(() => {
        updateActiveLink();
        ticking = false;
      });
      ticking = true;
    }
  }

  // Listen for scroll events
  window.addEventListener("scroll", handleScroll);

  // Set initial active link
  updateActiveLink();

  // Scroll to top button functionality
  const scrollToTopBtn = document.getElementById("scroll-to-top");

  if (scrollToTopBtn) {
    // Show/hide button based on scroll position
    function toggleScrollToTopBtn() {
      if (window.scrollY > 300) {
        scrollToTopBtn.classList.add("show");
      } else {
        scrollToTopBtn.classList.remove("show");
      }
    }

    // Scroll to top when button is clicked
    scrollToTopBtn.addEventListener("click", function () {
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    });

    // Add scroll listener for button visibility
    window.addEventListener("scroll", toggleScrollToTopBtn);

    // Initial check
    toggleScrollToTopBtn();
  }
});
