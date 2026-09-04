document.addEventListener("DOMContentLoaded", function () {
  /* ============================================================
       0. RESPONSIVE SIDEBAR TOGGLE & BACKDROP
       ============================================================ */
  const sidebarToggleBtn = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");

  // Create mobile backdrop dynamically if it doesn't exist
  let overlay = document.querySelector(".sidebar-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "sidebar-overlay";
    document.body.appendChild(overlay);
  }

  function isMobile() {
    return window.innerWidth <= 768;
  }

  function toggleSidebar() {
    if (!sidebar) return;

    if (isMobile()) {
      sidebar.classList.toggle("show");
      if (overlay) overlay.classList.toggle("show");
    } else {
      sidebar.classList.toggle("collapsed");
      document.body.classList.toggle(
        "sidebar-collapsed",
        sidebar.classList.contains("collapsed"),
      );
    }
  }

  function closeSidebarMobile() {
    if (sidebar) sidebar.classList.remove("show");
    if (overlay) overlay.classList.remove("show");
  }

  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleSidebar();
    });
  }

  if (overlay) {
    overlay.addEventListener("click", closeSidebarMobile);
  }

  // Handle screen resize to reset mobile states automatically
  window.addEventListener("resize", function () {
    if (window.innerWidth > 768) {
      if (sidebar) sidebar.classList.remove("show");
      if (overlay) overlay.classList.remove("show");
    }
  });

  /* ============================================================
       1. SIDEBAR: click parent module -> show/hide its children
       ============================================================ */
  const parentLinks = document.querySelectorAll(".parent-link");

  parentLinks.forEach(function (link) {
    link.addEventListener("click", function (e) {
      e.preventDefault();

      const menuItem = link.closest(".menu-item");
      const isOpen = menuItem.classList.contains("open");

      // Accordion behaviour: close any other open submenu first
      document.querySelectorAll(".menu-item.open").forEach(function (openItem) {
        if (openItem !== menuItem) {
          openItem.classList.remove("open");
        }
      });

      menuItem.classList.toggle("open", !isOpen);
    });
  });

  // Mark active link + auto-open its parent
  function setActiveModule(moduleKey) {
    document.querySelectorAll(".menu-link, .submenu a").forEach(function (a) {
      a.classList.remove("active", "active-item");
    });

    const target = document.querySelector('[data-module="' + moduleKey + '"]');
    if (!target) return;

    if (target.classList.contains("menu-link")) {
      target.classList.add("active");
    } else {
      target.classList.add("active-item");
    }

    const parentItem = target.closest(".menu-item");
    if (parentItem && parentItem.querySelector(".parent-link")) {
      parentItem.classList.add("open");
    }
  }

  // Clicking a leaf module link
  document.querySelectorAll("[data-module]").forEach(function (link) {
    link.addEventListener("click", function () {
      const moduleKey = link.getAttribute("data-module");
      setActiveModule(moduleKey);

      // Auto close sidebar on mobile when a link is clicked
      closeSidebarMobile();

      if (window.isDashboardPage) {
        loadModule(moduleKey);
      }
    });
  });

  // Auto-open active module on page load based on current URL
  (function autoOpenActiveModuleFromURL() {
    const currentPath = window.location.pathname;
    let matchedModule = null;

    document.querySelectorAll("[data-module]").forEach(function (link) {
      const href = link.getAttribute("href");
      if (!href || href === "#") return;
      if (link.pathname === currentPath) {
        matchedModule = link.getAttribute("data-module");
      }
    });

    if (matchedModule) {
      setActiveModule(matchedModule);
    }
  })();

  /* ============================================================
       1.1 SIDEBAR MENU FILTER/SEARCH
       ============================================================ */
  const menuSearchInput = document.getElementById("menu-search");
  if (menuSearchInput) {
    menuSearchInput.addEventListener("input", function () {
      const filter = this.value.toLowerCase().trim();
      const menuItems = document.querySelectorAll("#sidebar-menu .menu-item");

      menuItems.forEach(function (item) {
        const label = item.querySelector(".label")
          ? item.querySelector(".label").textContent.toLowerCase()
          : "";
        const subLinks = item.querySelectorAll(".submenu a");
        let hasMatch = label.includes(filter);

        subLinks.forEach(function (subLink) {
          if (subLink.textContent.toLowerCase().includes(filter)) {
            hasMatch = true;
            subLink.style.display = "";
          } else if (filter !== "") {
            subLink.style.display = "none";
          } else {
            subLink.style.display = "";
          }
        });

        if (hasMatch) {
          item.style.display = "";
          if (filter !== "" && item.classList.contains("has-children")) {
            item.classList.add("open");
          }
        } else {
          item.style.display = "none";
        }
      });

      if (filter === "") {
        document.querySelectorAll(".menu-item").forEach(function (item) {
          item.style.display = "";
          if (
            !item.querySelector(".active-item") &&
            !item.querySelector(".active")
          ) {
            item.classList.remove("open");
          }
        });
      }
    });
  }

  /* ============================================================
       2. HEADER: live date/time + logged-in user info
       ============================================================ */
  function updateClock() {
    const now = new Date();
    const dateStr = now.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
    const timeStr = now.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
    const dateEl = document.getElementById("nav-date");
    const timeEl = document.getElementById("nav-time");
    if (dateEl) dateEl.textContent = dateStr;
    if (timeEl) timeEl.textContent = timeStr;
  }
  updateClock();
  setInterval(updateClock, 1000 * 30);

  function fillUserInfo() {
    const user = window.dashboardUser || {};
    const nameEl = document.getElementById("nav-user-name");
    const roleEl = document.getElementById("nav-role");
    const counterEl = document.getElementById("nav-counter");
    if (nameEl) nameEl.textContent = user.username || "Guest";
    if (roleEl) roleEl.textContent = user.role || "User";
    if (counterEl) counterEl.textContent = user.counter || "1";
  }
  fillUserInfo();

  /* ============================================================
       3. CONTENT: widget cards — ONLY runs on the dashboard page
       ============================================================ */

  function loadModule(moduleKey) {
    renderModule(moduleKey);
  }

  if (window.isDashboardPage) {
    setActiveModule("dashboard");
    loadModule("dashboard");
  }
});
/* ==========================================================
   dashboard.js
   Vanilla JS, MPA-friendly. Pulls live numbers from the
   dashboard app's JSON/partial endpoints and refreshes them
   on an interval, matching the project's existing AJAX
   pattern (JSON for numbers, rendered HTML for row lists).
   ========================================================== */
(function () {
  "use strict";

  const ENDPOINTS = {
    kpis: "/dashboard/api/kpis/",
    salesTrend: "/dashboard/api/sales-trend/",
    topCategories: "/dashboard/api/top-categories/",
    recentSales: "/dashboard/api/recent-sales/",
    lowStock: "/dashboard/api/low-stock/",
    expiryAlert: "/dashboard/api/expiry-alerts/",
    expiryRows: "/dashboard/api/expiry-rows/",     
    pendingPO: "/dashboard/api/pending-po/",
    topProducts: "/dashboard/api/top-products/",
  };

  const REFRESH_MS = 60000; // auto-refresh every 60s
  let currentPeriod = "weekly";

  function fmtMoney(n) {
    const num = Number(n || 0);
    return (
      "Rs " +
      num.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  }

  function setLastUpdated() {
    const el = document.getElementById("dashLastUpdated");
    if (!el) return;
    const now = new Date();
    el.textContent =
      "Last updated at " +
      now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  async function getJSON(url) {
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!res.ok) throw new Error("Request failed: " + url);
    return res.json();
  }

  async function getHTML(url) {
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!res.ok) throw new Error("Request failed: " + url);
    return res.text();
  }

  /* ---------------- EXPIRY ALERTS BANNER ---------------- */
  async function loadExpiryAlerts() {
    const container = document.getElementById("expiryAlertsContainer");
    if (!container) return;

    try {
      const data = await getJSON(ENDPOINTS.expiryAlert);
      const expiredCount = data.expired_count || 0;
      const criticalCount = data.critical_count || 0;

      const expiryStatEl = document.getElementById("stat_expiry_count");
      if (expiryStatEl) {
        expiryStatEl.textContent = expiredCount + criticalCount;
      }

      container.innerHTML = "";

      if (expiredCount === 0 && criticalCount === 0) {
        container.innerHTML = `
          <div class="alert-banner alert-success" style="padding: 10px 14px; background: #ecfdf5; border: 1px solid #10b981; color: #065f46; border-radius: 6px; font-size: 0.875rem;">
            <span>✅ All stock is fresh! No batch expirations pending.</span>
          </div>
        `;
        return;
      }

      let html = "";
      if (expiredCount > 0) {
        html += `
          <div class="alert-banner alert-danger" style="padding: 10px 14px; background: #fef2f2; border: 1px solid #f87171; color: #991b1b; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; font-size: 0.875rem; margin-bottom: 8px;">
            <div><strong>🚨 Action Required:</strong> <span>${expiredCount} batch(es) have passed expiry date!</span></div>
            <a href="/inventory/wastage/create/" class="btn btn-sm" style="background: #dc2626; color: #fff; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 0.75rem;">Record Wastage</a>
          </div>
        `;
      }
      if (criticalCount > 0) {
        html += `
          <div class="alert-banner alert-warning" style="padding: 10px 14px; background: #fffbe2; border: 1px solid #facc15; color: #854d0e; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; font-size: 0.875rem;">
            <div><strong>⚠️ Expiry Warning:</strong> <span>${criticalCount} batch(es) expiring soon.</span></div>
            <a href="/inventory/expiry-report/?status=CRITICAL" class="btn btn-sm" style="background: #eab308; color: #fff; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 0.75rem;">View Report</a>
          </div>
        `;
      }

      container.innerHTML = html;
    } catch (err) {
      console.error("Expiry alert load failed:", err);
    }
  }

  
async function loadSalesTrend(period) {
    try {
        const data = await getJSON(
            ENDPOINTS.salesTrend + "?period=" + period
        );

        const container =
            document.getElementById("barChartContainer");

        const titleEl =
            document.getElementById("salesTrendTitle");

        const subtitleEl =
            document.getElementById("salesTrendSubtitle");

        if (!container) return;


        // ==========================================
        // UPDATE TITLE
        // ==========================================

        if (period === "weekly") {

            titleEl.innerText =
                "WEEKLY SALES (Rs. THOUSANDS)";

            subtitleEl.innerText =
                "Last 7 Days";

        } else {

            titleEl.innerText =
                "MONTHLY SALES (Rs. THOUSANDS)";

            subtitleEl.innerText =
                "Baisakh - Chaitra";
        }


        // ==========================================
        // FIND MAX VALUE
        // ==========================================

        const maxVal =
            Math.max(...data.values, 1);


        // ==========================================
        // CLEAR OLD BARS
        // ==========================================

        container.innerHTML = "";


        // ==========================================
        // CREATE BARS
        // ==========================================

        data.labels.forEach((label, index) => {

            const rawVal =
                Number(data.values[index] || 0);


            // Format displayed value
            const displayVal =
                rawVal >= 1000
                    ? rawVal.toLocaleString()
                    : rawVal.toFixed(0);


            // Calculate bar height
            const fillHeight =
                (rawVal / maxVal) * 100;


            // Last item = current day/month
            const isLastItem =
                index === data.labels.length - 1;


            // Create bar item
            const itemDiv =
                document.createElement("div");


            itemDiv.className =
                `bar-item ${isLastItem ? "is-current" : ""}`;


            // Store value for CSS
            itemDiv.dataset.value =
                rawVal;


            // Create HTML
            itemDiv.innerHTML = `
                <span class="bar-value">
                    ${displayVal}
                </span>

                <div class="bar-track">
                    <div
                        class="bar-fill"
                        style="height: ${fillHeight}%;">
                    </div>
                </div>

                <span class="bar-label">
                    ${label}
                </span>
            `;


            // IMPORTANT:
            // Add the generated bar to the chart
            container.appendChild(itemDiv);

        });


    } catch (err) {

        console.error(
            "Sales trend load failed:",
            err
        );

    }
}
  /* ---------------- ROW-PARTIAL WIDGETS ---------------- */
  async function loadPartial(endpoint, targetId, emptyColspan) {
    const target = document.getElementById(targetId);
    if (!target) return;
    try {
      const html = await getHTML(endpoint);
      target.innerHTML =
        html && html.trim() ? html : rowEmpty(emptyColspan, "Nothing to show.");
    } catch (err) {
      target.innerHTML = rowEmpty(emptyColspan, "Could not load data.");
      console.error(err);
    }
  }

  function rowEmpty(colspan, text) {
    return `<tr><td colspan="${colspan}" class="dash-table-empty">${text}</td></tr>`;
  }

  /* ---------------- REFRESH ORCHESTRATION ---------------- */
  function refreshAll() {
    loadExpiryAlerts();
    loadSalesTrend(currentPeriod);
    loadPartial(ENDPOINTS.expiryRows, "expiryRows", 5); // 👈 Fetch Expiry Table Rows
    loadPartial(ENDPOINTS.recentSales, "recentSalesRows", 4);
    loadPartial(ENDPOINTS.lowStock, "lowStockRows", 4);
    loadPartial(ENDPOINTS.pendingPO, "pendingPoRows", 4);
  }

  function initRefreshButton() {
    const btn = document.getElementById("dashRefreshBtn");
    if (!btn) return;
    btn.addEventListener("click", () => {
      btn.classList.add("is-spinning");
      refreshAll();
      setTimeout(() => btn.classList.remove("is-spinning"), 600);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initRefreshButton();
    refreshAll();
    setInterval(refreshAll, REFRESH_MS);
  });
})();
