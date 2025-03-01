// Toggle sidebar visibility
function toggleSidebar() {
    let sidebar = document.getElementById("sidebar");
    let content = document.getElementById("content");
    let graphFrame = document.getElementById("graph-frame");

    sidebar.classList.toggle("closed");
    graphFrame.classList.toggle("closed");

    if (sidebar.classList.contains("closed")) {
        content.style.marginLeft = "50px";
    } else {
        content.style.marginLeft = "250px";
    }
}

// Toggle visibility of AWS resource types (EC2, ASG, ELB, etc.)
function toggleResource(type) {
    fetch(`/toggle/${type}`, { method: "POST" })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                refreshGraph();
            } else {
                alert("Error toggling visibility!");
            }
        });
}

// Refresh the graph iframe to reflect new changes
function refreshGraph() {
    document.getElementById("graph-frame").contentWindow.location.reload();
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
