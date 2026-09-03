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
            document.body.classList.toggle("sidebar-collapsed", sidebar.classList.contains("collapsed"));
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

        document.querySelectorAll('[data-module]').forEach(function (link) {
            const href = link.getAttribute('href');
            if (!href || href === '#') return;
            if (link.pathname === currentPath) {
                matchedModule = link.getAttribute('data-module');
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
                const label = item.querySelector(".label") ? item.querySelector(".label").textContent.toLowerCase() : "";
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
                    if (!item.querySelector(".active-item") && !item.querySelector(".active")) {
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
        const dateStr = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
        const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
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
        pendingPO: "/dashboard/api/pending-po/",
        topProducts: "/dashboard/api/top-products/",
    };

    const REFRESH_MS = 60000; // auto-refresh every 60s
    let currentPeriod = "weekly";
    let salesChart = null;

    function fmtMoney(n) {
        const num = Number(n || 0);
        return "Rs " + num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function setLastUpdated() {
        const el = document.getElementById("dashLastUpdated");
        if (!el) return;
        const now = new Date();
        el.textContent = "Last updated at " + now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    async function getJSON(url) {
        const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        if (!res.ok) throw new Error("Request failed: " + url);
        return res.json();
    }

    async function getHTML(url) {
        const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        if (!res.ok) throw new Error("Request failed: " + url);
        return res.text();
    }

    /* ---------------- KPI strip ---------------- */
    function renderDelta(el, pct) {
        if (pct === null || pct === undefined || isNaN(pct)) {
            el.textContent = "";
            el.className = "stat-delta";
            return;
        }
        const rounded = Math.round(pct * 10) / 10;
        el.textContent = (rounded >= 0 ? "▲ " : "▼ ") + Math.abs(rounded) + "% vs yesterday";
        el.className = "stat-delta " + (rounded >= 0 ? "up" : "down");
    }

    async function loadKpis() {
        const strip = document.getElementById("kpiStrip");
        if (!strip) return;
        strip.querySelectorAll(".stat-card").forEach((c) => c.classList.add("is-loading"));
        try {
            const data = await getJSON(ENDPOINTS.kpis);

            setStat("today_sales", fmtMoney(data.today_sales), data.today_sales_change_pct);
            setStat("invoices_today", data.invoices_today, data.invoices_change_pct);
            setStat("net_profit", fmtMoney(data.net_profit), data.net_profit_change_pct);
            setStat("total_products", data.total_products);
            setStat("low_stock_count", data.low_stock_count);
            setStat("total_customers", data.total_customers);

            setLastUpdated();
        } catch (err) {
            console.error("KPI load failed:", err);
        } finally {
            strip.querySelectorAll(".stat-card").forEach((c) => c.classList.remove("is-loading"));
        }
    }

    function setStat(key, value, deltaPct) {
        const card = document.querySelector('.stat-card[data-stat="' + key + '"]');
        if (!card) return;
        const valueEl = card.querySelector(".stat-value");
        if (valueEl) valueEl.textContent = typeof value === "number" ? value.toLocaleString() : value;
        const deltaEl = card.querySelector("[data-delta]");
        if (deltaEl && deltaPct !== undefined) renderDelta(deltaEl, deltaPct);
    }
//---------- SALES TRENDS/ SALES DAYBYDAY
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

    function initPeriodToggle() {
        const buttons = document.querySelectorAll(".period-btn");
        buttons.forEach((btn) => {
            btn.addEventListener("click", () => {
                buttons.forEach((b) => b.classList.remove("is-active"));
                btn.classList.add("is-active");
                currentPeriod = btn.dataset.period;
                loadSalesTrend(currentPeriod);
            });
        });
    }


    /* ---------------- Top categories (bar list) ---------------- */
    async function loadTopCategories() {
        const list = document.getElementById("topCategoriesList");
        if (!list) return;
        try {
            const data = await getJSON(ENDPOINTS.topCategories);
            if (!data.length) {
                list.innerHTML = '<li class="bar-list-empty">No sales recorded yet.</li>';
                return;
            }
            list.innerHTML = data
                .map(
                    (cat) => `
                <li class="bar-list-item">
                    <div class="bar-list-row">
                        <span class="bar-list-name">${escapeHtml(cat.name)}</span>
                        <span class="bar-list-value">${fmtMoney(cat.total_sales)} · ${cat.pct}%</span>
                    </div>
                    <div class="bar-track"><div class="bar-fill" style="width:${cat.pct}%"></div></div>
                </li>`
                )
                .join("");
        } catch (err) {
            list.innerHTML = '<li class="bar-list-empty">Could not load categories.</li>';
            console.error(err);
        }
    }

    /* ---------------- Top products (bar list) ---------------- */
    async function loadTopProducts() {
        const list = document.getElementById("topProductsList");
        if (!list) return;
        try {
            const data = await getJSON(ENDPOINTS.topProducts);
            if (!data.length) {
                list.innerHTML = '<li class="bar-list-empty">No sales recorded yet.</li>';
                return;
            }
            list.innerHTML = data
                .map(
                    (p) => `
                <li class="bar-list-item">
                    <div class="bar-list-row">
                        <span class="bar-list-name">${escapeHtml(p.name)}</span>
                        <span class="bar-list-value">${p.units_sold} units</span>
                    </div>
                    <div class="bar-track"><div class="bar-fill" style="width:${p.pct}%"></div></div>
                </li>`
                )
                .join("");
        } catch (err) {
            list.innerHTML = '<li class="bar-list-empty">Could not load products.</li>';
            console.error(err);
        }
    }

    /* ---------------- Row-partial widgets (server-rendered HTML) ---------------- */
    async function loadPartial(endpoint, targetId, emptyColspan) {
        const target = document.getElementById(targetId);
        if (!target) return;
        try {
            const html = await getHTML(endpoint);
            target.innerHTML = html && html.trim() ? html : rowEmpty(emptyColspan, "Nothing to show.");
        } catch (err) {
            target.innerHTML = rowEmpty(emptyColspan, "Could not load data.");
            console.error(err);
        }
    }

    function rowEmpty(colspan, text) {
        return `<tr><td colspan="${colspan}" class="dash-table-empty">${text}</td></tr>`;
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    /* ---------------- Refresh orchestration ---------------- */
    function refreshAll() {
        loadKpis();
        loadSalesTrend(currentPeriod);
        loadTopCategories();
        loadTopProducts();
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
        initPeriodToggle();
        initRefreshButton();
        refreshAll();
        setInterval(refreshAll, REFRESH_MS);
    });
})();