// Toggle sidebar visibility
function toggleSidebar() {
    let sidebar = document.getElementById("sidebar");
    let content = document.getElementById("content");
    let toggleBtn = document.getElementById("toggle-btn");
    if (sidebar.classList.contains("collapsed")) {
        sidebar.classList.remove("collapsed");
        content.style.marginLeft = "250px";
        content.style.width = "calc(100% - 250px)";
        toggleBtn.style.left = "260px";
    } else {
        sidebar.classList.add("collapsed");
        content.style.marginLeft = "50px";
        content.style.width = "calc(100% - 50px)";
        toggleBtn.style.left = "60px";
    }
}

// Toggle details sidebar visibility
function toggleDetailsSidebar() {
    let detailsSidebar = document.getElementById("details-sidebar");
    let content = document.getElementById("content");
    let toggleDetailsBtn = document.getElementById("toggle-details-btn");
    if (detailsSidebar.classList.contains("collapsed")) {
        detailsSidebar.classList.remove("collapsed");
        content.style.width = "calc(100% - 500px)";
        toggleDetailsBtn.style.right = "260px";
    } else {
        detailsSidebar.classList.add("collapsed");
        content.style.width = "calc(100% - 250px)";
        toggleDetailsBtn.style.right = "10px";
    }
}

// Toggle visibility of AWS resource types (EC2, ASG, ELB, etc.)
function toggleVisibility(resourceType) {
    fetch(`/toggle/${resourceType}`, { method: "POST" })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                refreshGraph();
                fetchDetails(resourceType);
            }
        });
}

// Refresh the graph iframe to reflect new changes
function refreshGraph() {
    document.getElementById("graph-frame").contentWindow.location.reload();
}

function fetchDetails(resourceType) {
    fetch(`/details/${resourceType}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                let detailsSidebar = document.getElementById("details-sidebar");
                let detailsTitle = document.getElementById("details-title");
                let detailsList = document.getElementById("details-list");
                let detailsTableBody = document.getElementById("details-table-body");

                detailsTitle.textContent = `${resourceType.toUpperCase()} Details`;
                detailsList.innerHTML = "";
                detailsTableBody.innerHTML = "";

                data.details.forEach(detail => {
                    let listItem = document.createElement("li");
                    listItem.textContent = detail;
                    detailsList.appendChild(listItem);

                    let tableRow = document.createElement("tr");
                    let tableCell = document.createElement("td");
                    tableCell.textContent = detail;
                    tableRow.appendChild(tableCell);
                    detailsTableBody.appendChild(tableRow);
                });

                detailsSidebar.classList.remove("collapsed");
                adjustGraphWidth();
            } else {
                alert("Error fetching details!");
            }
        });
}

function adjustGraphWidth() {
    let detailsSidebar = document.getElementById("details-sidebar");
    let content = document.getElementById("content");
    if (detailsSidebar.classList.contains("collapsed")) {
        content.style.width = "calc(100% - 250px)";
    } else {
        content.style.width = "calc(100% - 500px)";
    }
}

// Auto-update the graph by fetching new AWS data
function autoUpdate() {
    fetch("/update")
        .then(response => response.json())
        .then(data => {
            console.log(data.message);
            refreshGraph();
        });
}

// Set auto-update interval (default: 2 minutes)
let updateInterval = 120000;  // Default to 2 min
let updateTimer = setInterval(autoUpdate, updateInterval);

// Update the auto-update frequency based on user selection
function setAutoUpdateInterval(interval) {
    clearInterval(updateTimer);
    updateInterval = interval;
    updateTimer = setInterval(autoUpdate, updateInterval);
}

// Listen for user selection of auto-update intervals
document.addEventListener("DOMContentLoaded", function () {
    let intervalSelector = document.getElementById("update-interval");
    if (intervalSelector) {
        intervalSelector.addEventListener("change", function () {
            let selectedValue = parseInt(this.value) * 60000; // Convert minutes to milliseconds
            setAutoUpdateInterval(selectedValue);
        });
    }
});
