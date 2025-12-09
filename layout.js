async function loadPart(id, file) {
    const element = document.getElementById(id);
    const response = await fetch(file);
    element.innerHTML = await response.text();
}

// cargar partes comunes
loadPart("header", "header.html");
loadPart("footer", "footer.html");
