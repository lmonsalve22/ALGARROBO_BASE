function renderHeader2(containerId = "headerRender") {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error("No existe el contenedor:", containerId);
        return;
    }

    container.innerHTML = `
    <header class="bg-blue-600 text-white shadow-lg relative z-40">
        <div class="container mx-auto px-4 py-3">
            <div class="flex justify-between items-center">
                <div class="flex items-center space-x-4">
                    <i class="fas fa-city text-2xl"></i>
                    <div>
                        <h1 class="text-xl font-bold">Geoportal Municipal</h1>
                        <p class="text-xs text-blue-100">Ilustre Municipalidad de Algarrobo</p>
                    </div>
                </div>
                <div class="flex items-center space-x-4">
                    <div class="relative">
                        <button onclick="toggleUserMenu()" class="flex items-center space-x-2 hover:bg-blue-700 px-3 py-2 rounded">
                            <i class="fas fa-user-circle"></i>
                            <span id="currentRole">Administrador</span>
                            <i class="fas fa-chevron-down text-xs"></i>
                        </button>
                        <div id="userMenu" class="hidden absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-xl z-50">
                            <a href="#" onclick="changeRole('admin')" class="block px-4 py-2 text-gray-800 hover:bg-gray-100">
                                <i class="fas fa-user-shield mr-2"></i> Administrador
                            </a>
                            <a href="#" onclick="changeRole('alcalde')" class="block px-4 py-2 text-gray-800 hover:bg-gray-100">
                                <i class="fas fa-user-tie mr-2"></i> Alcalde
                            </a>
                            <a href="#" onclick="changeRole('secplac')" class="block px-4 py-2 text-gray-800 hover:bg-gray-100">
                                <i class="fas fa-users mr-2"></i> SECPLAC
                            </a>
                            <a href="#" onclick="changeRole('public')" class="block px-4 py-2 text-gray-800 hover:bg-gray-100">
                                <i class="fas fa-eye mr-2"></i> Vista Pública
                            </a>
                            <hr class="my-1">
                            <a href="#" class="block px-4 py-2 text-gray-800 hover:bg-gray-100">
                                <i class="fas fa-cog mr-2"></i> Configuración
                            </a>
                            <a href="#" onclick="logout()" class="block px-4 py-2 text-gray-800 hover:bg-gray-100">
                                <i class="fas fa-sign-out-alt mr-2"></i> Salir
                            </a>
                        </div>
                    </div>
                    <button onclick="toggleNotifications()" class="relative hover:bg-blue-700 p-2 rounded">
                        <i class="fas fa-bell"></i>
                        <span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">3</span>
                    </button>
                </div>
            </div>
        </div>
    </header>
    `;
}

function renderHeader(containerId = "headerRender") {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error("No existe el contenedor:", containerId);
        return;
    }

    // Seguridad mínima
    const roleName = userData?.roles?.[0]?.nombre ?? "Sin rol";

    container.innerHTML = `
    <header class="bg-blue-600 text-white shadow-lg relative z-40">
        <div class="container mx-auto px-4 py-3">
            <div class="flex justify-between items-center">
                
                <div class="flex items-center space-x-4">
                    <i class="fas fa-city text-2xl"></i>
                    <div>
                        <h1 class="text-xl font-bold">Geoportal Municipal</h1>
                        <p class="text-xs text-blue-100">Ilustre Municipalidad de Algarrobo</p>
                    </div>
                </div>

                <div class="flex items-center space-x-4">
                    
                    <div class="relative">
                        <button onclick="toggleUserMenu()" 
                                class="flex items-center space-x-2 hover:bg-blue-700 px-3 py-2 rounded">
                            <i class="fas fa-user-circle"></i>
                            <span id="currentRole">${roleName}</span>
                            <i class="fas fa-chevron-down text-xs"></i>
                        </button>

                        <div id="userMenu" 
                             class="hidden absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-xl z-50">

                            <a href="#" 
                               class="block px-4 py-2 text-gray-800 hover:bg-gray-100">
                                <i class="fas fa-cog mr-2"></i> Configuración
                            </a>

                            <a href="#" 
                               onclick="logout()" 
                               class="block px-4 py-2 text-gray-800 hover:bg-gray-100">
                                <i class="fas fa-sign-out-alt mr-2"></i> Salir
                            </a>
                        </div>
                    </div>

                    <button onclick="toggleNotifications()" 
                            class="relative hover:bg-blue-700 p-2 rounded">
                        <i class="fas fa-bell"></i>
                        <span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs 
                                     rounded-full h-5 w-5 flex items-center justify-center">3</span>
                    </button>

                </div>
            </div>
        </div>
    </header>
    `;
}


function renderSidebar2(containerId = "sidebarContainer") {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error("No existe el contenedor:", containerId);
        return;
    }

    // Ruta actual (ej: "/frontend/division/secplan/admin_general/proyecto.html")
    const currentPath = window.location.pathname.split("/").pop();

    // Diccionario de páginas → nombre exacto del archivo
    const pages = {
        dashboard: "dashboard.html",
        proyecto: "proyecto.html",
        mapa: "mapa.html",
        informe: "informe.html",
        calendario: "calendario.html"
    };

    // Función para saber si está activo
    const isActive = (file) =>
        currentPath === file
            ? "bg-blue-50 text-blue-600"
            : "hover:bg-blue-50 text-gray-700";

    container.innerHTML = `
    <aside id="sidebar" class="w-64 bg-white shadow-lg h-screen sticky top-0 sidebar-transition z-30">
        <nav class="p-4">
            <ul class="space-y-2">

                <li>
                    <a href="${pages.dashboard}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.dashboard)}">
                        <i class="fas fa-tachometer-alt w-5"></i>
                        <span>Dashboard</span>
                    </a>
                </li>

                <li>
                    <a href="${pages.proyecto}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.proyecto)}">
                        <i class="fas fa-map-marked-alt w-5"></i>
                        <span>Proyectos</span>
                    </a>
                </li>

                <li>
                    <a href="${pages.mapa}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.mapa)}">
                        <i class="fas fa-map-marked-alt w-5"></i>
                        <span>Mapa</span>
                    </a>
                </li>

                <li>
                    <a href="${pages.informe}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.informe)}">
                        <i class="fas fa-chart-bar w-5"></i>
                        <span>Informes</span>
                    </a>
                </li>

                <li>
                    <a href="${pages.calendario}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.calendario)}">
                        <i class="fas fa-calendar-alt w-5"></i>
                        <span>Calendario</span>
                    </a>
                </li>


                <li class="pt-4 mt-4 border-t">
                    <p class="text-xs text-gray-500 uppercase font-semibold px-3">Módulos</p>
                </li>

                <li>
                    <a href="#" class="nav-item flex items-center space-x-3 p-3 rounded-lg hover:bg-blue-50 text-gray-700">
                        <i class="fas fa-road w-5"></i>
                        <span>Vialidad</span>
                    </a>
                </li>

                <li>
                    <a href="#" class="nav-item flex items-center space-x-3 p-3 rounded-lg hover:bg-blue-50 text-gray-700">
                        <i class="fas fa-tint w-5"></i>
                        <span>Saneamiento</span>
                    </a>
                </li>

                <li>
                    <a href="#" class="nav-item flex items-center space-x-3 p-3 rounded-lg hover:bg-blue-50 text-gray-700">
                        <i class="fas fa-tree w-5"></i>
                        <span>Espacios Públicos</span>
                    </a>
                </li>

            </ul>
        </nav>
    </aside>
    `;
}

function renderSidebar(containerId = "sidebarContainer") {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error("No existe el contenedor:", containerId);
        return;
    }

    // Validación básica de userData
    const nivelAcceso = userData?.nivel_acceso ?? null;

    // Ruta actual (ej: "/frontend/division/secplan/admin_general/proyecto.html")
    const currentPath = window.location.pathname.split("/").pop();

    // Diccionario de páginas → nombre exacto del archivo
    const pages = {
        dashboard: "dashboard.html",
        proyecto: "proyecto.html",
        mapa: "mapa.html",
        informe: "informe.html",
        calendario: "calendario.html"
    };

    // Función para saber si está activo
    const isActive = (file) =>
        currentPath === file
            ? "bg-blue-50 text-blue-600"
            : "hover:bg-blue-50 text-gray-700";

    // Render condicional de módulos (solo nivel_acceso === 10)
    const modulosHTML = nivelAcceso === 10 ? `
        <li class="pt-4 mt-4 border-t">
            <p class="text-xs text-gray-500 uppercase font-semibold px-3">Módulos</p>
        </li>

        <li>
            <a href="#" class="nav-item flex items-center space-x-3 p-3 rounded-lg hover:bg-blue-50 text-gray-700">
                <i class="fas fa-road w-5"></i>
                <span>Vialidad</span>
            </a>
        </li>

        <li>
            <a href="#" class="nav-item flex items-center space-x-3 p-3 rounded-lg hover:bg-blue-50 text-gray-700">
                <i class="fas fa-tint w-5"></i>
                <span>Saneamiento</span>
            </a>
        </li>

        <li>
            <a href="#" class="nav-item flex items-center space-x-3 p-3 rounded-lg hover:bg-blue-50 text-gray-700">
                <i class="fas fa-tree w-5"></i>
                <span>Espacios Públicos</span>
            </a>
        </li>
    ` : "";

    container.innerHTML = `
    <aside id="sidebar" class="w-64 bg-white shadow-lg h-screen sticky top-0 sidebar-transition z-30">
        <nav class="p-4">
            <ul class="space-y-2">

                <li>
                    <a href="${pages.dashboard}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.dashboard)}">
                        <i class="fas fa-tachometer-alt w-5"></i>
                        <span>Dashboard</span>
                    </a>
                </li>

                <li>
                    <a href="${pages.proyecto}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.proyecto)}">
                        <i class="fas fa-map-marked-alt w-5"></i>
                        <span>Proyectos</span>
                    </a>
                </li>

                <li>
                    <a href="${pages.mapa}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.mapa)}">
                        <i class="fas fa-map-marked-alt w-5"></i>
                        <span>Mapa</span>
                    </a>
                </li>

                <li>
                    <a href="${pages.informe}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.informe)}">
                        <i class="fas fa-chart-bar w-5"></i>
                        <span>Informes</span>
                    </a>
                </li>

                <li>
                    <a href="${pages.calendario}" class="nav-item flex items-center space-x-3 p-3 rounded-lg ${isActive(pages.calendario)}">
                        <i class="fas fa-calendar-alt w-5"></i>
                        <span>Calendario</span>
                    </a>
                </li>

                ${modulosHTML}

            </ul>
        </nav>
    </aside>
    `;
}


renderHeader("headerRender")
renderSidebar("asideRender")
