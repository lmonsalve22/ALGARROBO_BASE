/**
 * Sidebar Loader for Transparencia Module
 * Injects sidebar.html and handles relative paths and active states.
 */
(function () {
    function initSidebar() {
        const sidebarContainer = document.querySelector('aside.sidebar');
        if (!sidebarContainer) return;

        // Determine path depth relative to index folder
        const path = window.location.pathname;
        let prefix = "";

        // Check if we are in a subfolder
        const subfolders = ['/persona/', '/registro/', '/remuneracion/'];
        const isInSubfolder = subfolders.some(sf => path.includes(sf));

        if (isInSubfolder) {
            prefix = "../";
        } else {
            prefix = "./";
        }

        fetch(prefix + 'sidebar.html')
            .then(response => {
                if (!response.ok) throw new Error("Sidebar file not found");
                return response.text();
            })
            .then(html => {
                sidebarContainer.innerHTML = html;

                // Define destination links
                const links = {
                    home: prefix + "../../../../administracion/index.html",
                    pagos: prefix + "inicio.html",
                    remuneracion: prefix + "remuneracion_bruta.html",
                    persona: prefix + "rutUnico.html"
                };

                // Update hrefs and set active classes
                const navLinks = sidebarContainer.querySelectorAll('.nav-tab');
                navLinks.forEach(link => {
                    const navId = link.getAttribute('data-nav');
                    if (links[navId]) {
                        link.href = links[navId];
                    }

                    // Logic for "active" class
                    let isActive = false;
                    const fileName = path.split('/').pop();

                    if (navId === 'pagos' && fileName === 'inicio.html') {
                        isActive = true;
                    } else if (navId === 'remuneracion') {
                        if (fileName === 'remuneracion_bruta.html' || path.includes('/remuneracion/')) {
                            isActive = true;
                        }
                    } else if (navId === 'persona') {
                        if (fileName === 'rutUnico.html' || path.includes('/persona/') || path.includes('/registro/')) {
                            isActive = true;
                        }
                    }

                    if (isActive) {
                        link.classList.add('active');
                    } else {
                        link.classList.remove('active');
                    }
                });

                // Initialize icons
                if (window.lucide) {
                    window.lucide.createIcons();
                }
            })
            .catch(err => console.error("Error loading sidebar:", err));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSidebar);
    } else {
        initSidebar();
    }
})();
