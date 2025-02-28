function toggleSidebar() {
    let sidebar = document.getElementById("sidebar");
    let graphFrame = document.getElementById("graph-frame");
    sidebar.classList.toggle("closed");
    graphFrame.classList.toggle("closed");
}

function toggleResource(type) {
    let nodes = document.querySelectorAll(`.${type}`);
    nodes.forEach(node => node.style.display = node.style.display === "none" ? "block" : "none");
}

function autoUpdate() {
    fetch("/update").then(response => response.json()).then(data => {
        console.log(data.message);
        document.getElementById("graph-frame").contentWindow.location.reload();
    });
}

setInterval(autoUpdate, 120000);
