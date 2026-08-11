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
    const moduleWidgets = {
        dashboard: [
            { id: "w-today-sales", label: "TODAY'S SALES", endpoint: "/api/dashboard/today-sales/",
              demo: { value: "₹ 48,320", sub: "+12.4% vs yesterday" } },
            { id: "w-total-products", label: "TOTAL PRODUCTS", endpoint: "/api/dashboard/total-products/",
              demo: { value: "2,847", sub: "34 low stock alerts" } },
            { id: "w-invoices-today", label: "INVOICES TODAY", endpoint: "/api/dashboard/invoices-today/",
              demo: { value: "163", sub: "12 pending payment" } },
            { id: "w-net-profit", label: "NET PROFIT (MONTH)", endpoint: "/api/dashboard/net-profit/",
              demo: { value: "₹ 1,24,580", sub: "Target: ₹ 1,50,000" } },
            { id: "w-top-categories", label: "TOP CATEGORIES", endpoint: "/api/dashboard/top-categories/",
              span2: true, isBarList: true,
              demo: { items: [
                  { name: "Biscuits & Cookies", count: 842, pct: 90 },
                  { name: "Beverages", count: 634, pct: 70 },
                  { name: "Dairy Products", count: 521, pct: 58 },
                  { name: "Personal Care", count: 410, pct: 46 }
              ] } }
        ]
    };

    function renderWidgetCard(widget) {
        const card = document.createElement("div");
        card.className = "widget-card" + (widget.span2 ? " span-2" : "");
        card.id = widget.id;
        card.innerHTML =
            '<div class="w-label">' + widget.label + '</div>' +
            '<div class="w-loading">Loading...</div>';
        return card;
    }

    function renderModule(moduleKey) {
        const contentEl = document.getElementById("content");
        if (!contentEl) return;

        const widgets = moduleWidgets[moduleKey];
        contentEl.innerHTML = "";

        if (!widgets) {
            contentEl.innerHTML = '<div class="widget-card span-2"><div class="w-label">' +
                moduleKey.toUpperCase().replace(/-/g, " ") +
                '</div><div class="w-sub">This module\'s widgets are not configured yet.</div></div>';
            return;
        }

        widgets.forEach(function (widget) {
            const card = renderWidgetCard(widget);
            contentEl.appendChild(card);
            loadWidgetData(widget, card);
        });
    }

    function loadWidgetData(widget, card) {
        fetch(widget.endpoint)
            .then(function (res) {
                if (!res.ok) throw new Error("API not ready");
                return res.json();
            })
            .then(function (data) {
                renderWidgetContent(widget, card, data);
            })
            .catch(function () {
                renderWidgetContent(widget, card, widget.demo);
            });
    }

    function renderWidgetContent(widget, card, data) {
        if (widget.isBarList) {
            let html = '<div class="w-label">' + widget.label + '</div>';
            data.items.forEach(function (item) {
                html +=
                    '<div class="bar-row"><span>' + item.name + '</span>' +
                    '<span class="w-sub">' + item.count + ' sold</span></div>' +
                    '<div class="bar-track"><div class="bar-fill" style="width:' + item.pct + '%;"></div></div>';
            });
            card.innerHTML = html;
        } else {
            card.innerHTML =
                '<div class="w-label">' + widget.label + '</div>' +
                '<div class="w-value">' + data.value + '</div>' +
                '<div class="w-sub">' + data.sub + '</div>';
        }
    }

    function loadModule(moduleKey) {
        renderModule(moduleKey);
    }

    if (window.isDashboardPage) {
        setActiveModule("dashboard");
        loadModule("dashboard");
    }

});