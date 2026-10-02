const menuButton = document.querySelector(".menu-toggle");
const siteLinks = document.querySelector(".nav-links");

menuButton.addEventListener("click", () => {
  const isOpen = menuButton.getAttribute("aria-expanded") === "true";
  menuButton.setAttribute("aria-expanded", String(!isOpen));
  siteLinks.classList.toggle("is-open", !isOpen);
});

siteLinks.addEventListener("click", (event) => {
  if (event.target.closest("a")) {
    menuButton.setAttribute("aria-expanded", "false");
    siteLinks.classList.remove("is-open");
  }
});

document.querySelectorAll("[role='tablist']").forEach((tabList) => {
  const tabs = Array.from(tabList.querySelectorAll("[role='tab']"));

  function activateTab(selectedTab, moveFocus = false) {
    tabs.forEach((tab) => {
      const isSelected = tab === selectedTab;
      tab.setAttribute("aria-selected", String(isSelected));
      tab.tabIndex = isSelected ? 0 : -1;
      document.getElementById(tab.getAttribute("aria-controls")).hidden = !isSelected;
    });

    if (moveFocus) selectedTab.focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activateTab(tab));
    tab.addEventListener("keydown", (event) => {
      let nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      if (nextIndex !== index) {
        event.preventDefault();
        activateTab(tabs[nextIndex], true);
      }
    });
  });
});

function applyCountryDisplayLimits(panelSelector, entrySelector) {
  document.querySelectorAll(panelSelector).forEach((panel) => {
    const requestedCount = Number(panel.dataset.visibleCount);
    const entries = Array.from(panel.querySelectorAll(entrySelector));
    const visibleCount = Math.min(requestedCount, entries.length);
    entries.forEach((entry, index) => {
      entry.hidden = index >= visibleCount;
    });

    const tab = document.getElementById(panel.getAttribute("aria-labelledby"));
    const countBadge = tab?.querySelector("span");
    if (countBadge) countBadge.textContent = String(visibleCount).padStart(2, "0");
  });
}

applyCountryDisplayLimits("#clients .client-panel", ".client-entry");
applyCountryDisplayLimits("#feedback .client-panel", ".review-entry");

const reviewServices = new Map([
  ["Little Caesars", ["Payroll", "Camera monitoring", "Account management", "Inventory management", "Employee data management"]],
  ["Cheezy Blast Pizza", ["Social media management", "Advertisement design", "Reels editing", "Business video production"]],
  ["GlowNest Beauty Studio", ["Graphic design", "Social media design", "Video editing"]],
  ["Shree Krishna Saree House", ["E-commerce website", "Product catalogue", "Social media marketing", "WhatsApp marketing", "Customer data management"]],
  ["Urban Chai Café", ["Website", "Social media marketing", "Food/product photography", "Reels editing"]],
  ["PixelCraft Studio", ["Graphic design", "Video editing", "Motion graphics", "Social media design", "Advertisement design"]],
  ["RoyalRide Travels", ["Website", "CRM automation", "WhatsApp automation", "Customer management"]],
  ["Aarohi Education Hub", ["School/college website", "Data management", "Back-office support", "Document management", "MIS preparation"]],
  ["FinEdge Advisors", ["Bookkeeping", "Financial reports", "MIS reports", "Data management", "Business performance analysis"]],
  ["QuickKart Online", ["E-commerce website", "SEO", "Lead generation", "Customer acquisition", "Marketing automation"]],
  ["SafeWatch 360", ["Remote CCTV monitoring", "AI CCTV monitoring", "Multi-location monitoring", "Security dashboard", "Incident monitoring"]],
  ["BuildMint Consultants", ["Business consulting", "Market analysis", "Business planning", "Business growth planning", "Performance analysis"]],
  ["StyleAura Boutique", ["Product catalogue", "Social media design", "Product video editing", "E-commerce website"]],
  ["DataNest Solutions", ["Data entry", "Data cleaning", "Excel dashboards", "Power BI dashboards", "Automated reports", "Data analysis"]],
  ["BluePeak Realty", ["Website", "SEO", "Lead generation"]],
  ["BurgerBolt Kitchen", ["Creative marketing material", "Social media support"]],
  ["CloudBridge Consulting", ["Remote IT support", "Cloud solutions"]],
  ["LedgerLoop", ["Bookkeeping", "Financial reporting"]],
  ["BrightFrame Media", ["Video editing", "Motion graphics"]],
  ["NovaNest E-Commerce", ["E-commerce", "Customer management", "Automation"]],
  ["WatchGrid Security", ["Remote CCTV monitoring", "Incident monitoring"]],
  ["TaskPilot AI", ["AI automation", "Customer workflows", "Reporting tasks"]],
  ["MapleMunch Café", ["Website", "Social media marketing", "Menu design", "Food video editing"]],
  ["NorthStar Properties", ["Real estate website", "SEO", "Lead generation", "Google Business Profile"]],
  ["TrueNorth Books", ["Bookkeeping", "Payroll processing", "Financial reports", "Expense management"]],
  ["CodeHarbor Digital", ["Custom software", "CRM software", "Cloud solutions", "Remote IT support", "Database management"]],
  ["Velvet Maple Boutique", ["E-commerce website", "Product catalogue", "Social media design", "Product video editing"]],
  ["DataPeak Analytics", ["Data analysis", "Power BI dashboards", "Business intelligence", "Predictive analytics", "Automated reports"]],
  ["SafeVision Canada", ["Remote CCTV monitoring", "AI CCTV monitoring", "Security alerts", "Multi-location monitoring"]],
  ["WorkNest HR", ["Employee database management", "Recruitment support", "Payroll", "HR reports", "Employee documentation"]],
  ["Crust & Ember", ["Website", "Social media marketing", "Advertisement design"]],
  ["PrimeNest Properties", ["Real estate website", "SEO", "Lead generation", "Social media marketing", "CRM automation"]],
  ["LedgerBee UK", ["Bookkeeping", "Billing and invoicing", "Financial reports", "MIS reports"]],
  ["PixelRush Studio", ["Graphic design", "Video editing", "Motion graphics", "Social media design", "Explainer videos"]],
  ["TaskForge UK", ["Business process automation", "CRM automation", "Email automation", "Reporting automation", "AI workflow automation"]],
  ["BritStyle Collective", ["E-commerce website", "Product catalogue", "Branding", "Social media marketing"]],
  ["WatchTower 360", ["Remote CCTV monitoring", "AI video analytics", "Security dashboard", "Incident monitoring"]],
  ["GreenGrid Consulting", ["Business consulting", "Market research", "Business strategy", "Digital transformation consulting"]],
  ["Coastal Crust Pizza", ["Website", "Social media marketing", "Advertisement design", "Reels editing"]],
  ["AussieNest Realty", ["Real estate website", "SEO", "Lead generation", "Google Business Profile", "CRM automation"]],
  ["SwiftBooks AU", ["Bookkeeping", "Payroll processing", "Financial reports", "Cash-flow analysis"]],
  ["SparkByte Digital", ["Custom software", "Mobile app development", "Cloud solutions", "Remote IT support"]],
  ["Brew & Bloom Café", ["Website", "Menu design", "Social media design"]],
  ["VisionShield AU", ["Remote CCTV monitoring", "AI video analytics", "Multi-location monitoring", "Security alerts", "Remote security dashboard"]],
  ["AutoPilot Hub", ["AI chatbots", "AI customer support", "AI agents", "Workflow automation", "WhatsApp automation", "AI reporting"]],
  ["DataWave Analytics", ["Data cleaning", "Data analysis", "KPI dashboards", "Power BI dashboards", "Business forecasting"]],
]);

document.querySelectorAll(".review-entry").forEach((entry) => {
  const clientName = entry.querySelector("h3").textContent.trim();
  const services = reviewServices.get(clientName);
  if (!services) return;

  const serviceDetails = document.createElement("dl");
  serviceDetails.className = "review-services";
  const label = document.createElement("dt");
  label.textContent = "Services";
  const list = document.createElement("dd");
  list.textContent = services.join(", ");
  serviceDetails.append(label, list);
  entry.append(serviceDetails);
});

document.querySelectorAll("#feedback .client-panel").forEach((panel) => {
  const reviewGrid = panel.querySelector(".review-grid");
  const reviewTable = document.createElement("table");
  reviewTable.className = "review-table";

  const caption = document.createElement("caption");
  caption.className = "visually-hidden";
  caption.textContent = `${document.getElementById(panel.getAttribute("aria-labelledby")).textContent.trim()} sample client ratings, feedback, and services`;

  const columnGroup = document.createElement("colgroup");
  for (let columnIndex = 0; columnIndex < 4; columnIndex += 1) {
    columnGroup.append(document.createElement("col"));
  }

  const tableHead = document.createElement("thead");
  const headingRow = document.createElement("tr");
  ["Client", "Rating", "Feedback", "Services"].forEach((headingText) => {
    const heading = document.createElement("th");
    heading.scope = "col";
    heading.textContent = headingText;
    headingRow.append(heading);
  });
  tableHead.append(headingRow);

  const tableBody = document.createElement("tbody");
  reviewGrid.querySelectorAll(".review-entry").forEach((entry) => {
    const row = document.createElement("tr");
    row.hidden = entry.hidden;

    const clientName = document.createElement("th");
    clientName.scope = "row";
    clientName.textContent = entry.querySelector("h3").textContent.trim();

    const rating = document.createElement("td");
    rating.className = "review-score";
    rating.dataset.label = "Rating";
    rating.textContent = entry.querySelector(".review-score").textContent.trim();

    const feedbackCell = document.createElement("td");
    feedbackCell.dataset.label = "Feedback";
    const feedback = document.createElement("blockquote");
    feedback.textContent = entry.querySelector("blockquote").textContent.trim();
    feedbackCell.append(feedback);

    const services = document.createElement("td");
    services.dataset.label = "Services";
    services.textContent = entry.querySelector(".review-services dd").textContent.trim();

    row.append(clientName, rating, feedbackCell, services);
    tableBody.append(row);
  });

  reviewTable.append(caption, columnGroup, tableHead, tableBody);
  reviewGrid.replaceWith(reviewTable);
});

const serviceSearch = document.querySelector("#service-search");
const serviceCount = document.querySelector("#service-count");
const serviceEmptyMessage = document.querySelector("#service-search-empty");
const serviceDepartments = Array.from(document.querySelectorAll(".service-department"));
const totalServices = serviceDepartments.reduce(
  (total, department) => total + department.querySelectorAll(".service-list li").length,
  0,
);

serviceDepartments.forEach((department) => {
  const count = department.querySelectorAll(".service-list li").length;
  department.querySelector(".service-department-count").textContent = `${count} services`;
});

serviceCount.textContent = `${totalServices} services across ${serviceDepartments.length} departments`;

serviceSearch.addEventListener("input", () => {
  const query = serviceSearch.value.trim().toLocaleLowerCase();
  let matchingServiceCount = 0;
  let matchingDepartmentCount = 0;

  serviceDepartments.forEach((department) => {
    const departmentMatches = department.querySelector(".service-department-title").textContent.toLocaleLowerCase().includes(query);
    let departmentHasMatch = departmentMatches;
    const subgroups = Array.from(department.querySelectorAll(".service-subgroup"));

    subgroups.forEach((subgroup) => {
      const subgroupMatches = subgroup.querySelector("h3").textContent.toLocaleLowerCase().includes(query);
      const services = Array.from(subgroup.querySelectorAll(".service-list li"));
      let subgroupHasMatch = subgroupMatches || departmentMatches;

      services.forEach((service) => {
        const serviceMatches = service.textContent.toLocaleLowerCase().includes(query);
        const isVisible = !query || departmentMatches || subgroupMatches || serviceMatches;
        service.hidden = !isVisible;
        if (isVisible) {
          matchingServiceCount += 1;
          subgroupHasMatch = true;
        }
      });

      subgroup.hidden = Boolean(query) && !subgroupHasMatch;
      departmentHasMatch = departmentHasMatch || subgroupHasMatch;
    });

    department.hidden = Boolean(query) && !departmentHasMatch;
    if (departmentHasMatch) matchingDepartmentCount += 1;
    if (query) department.open = departmentHasMatch;
  });

  serviceEmptyMessage.hidden = matchingDepartmentCount > 0;
  serviceCount.dataset.state = matchingDepartmentCount === 0 ? "empty" : "";
  serviceCount.textContent = query
    ? `${matchingServiceCount} matching services in ${matchingDepartmentCount} departments`
    : `${totalServices} services across ${serviceDepartments.length} departments`;
});

const inquiryForm = document.querySelector(".inquiry-form");
const formStatus = document.querySelector(".form-status");

inquiryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = inquiryForm.querySelector("[type='submit']");
  const originalButtonText = submitButton.textContent;
  submitButton.disabled = true;
  submitButton.textContent = "Sending...";
  inquiryForm.setAttribute("aria-busy", "true");
  formStatus.textContent = "";
  formStatus.removeAttribute("data-state");

  try {
    const inquiryPayload = Object.fromEntries(new FormData(inquiryForm).entries());
    const response = await fetch(inquiryForm.action, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(inquiryPayload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Unable to send your enquiry.");
    inquiryForm.reset();
    formStatus.textContent = result.sheetSaved === true
      ? "Your enquiry was emailed and saved to the private sheet."
      : result.sheetSaved === false
        ? "Your enquiry was emailed, but could not be saved to the private sheet."
        : "Thanks. Your enquiry has been sent to our email.";
  } catch (error) {
    formStatus.dataset.state = "error";
    formStatus.textContent = error.message || "Unable to send your enquiry. Please email us directly.";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = originalButtonText;
    inquiryForm.removeAttribute("aria-busy");
  }
});

document.querySelector("#year").textContent = new Date().getFullYear();