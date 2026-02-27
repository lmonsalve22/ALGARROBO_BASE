
function renderHeader(containerId = "headerRender") {
    const container = document.getElementById(containerId);
    if (!container) return;

    let user = typeof userData !== 'undefined' ? userData : null;
    if (!user) {
        try {
            const stored = localStorage.getItem('userData') || localStorage.getItem('user_data') || localStorage.getItem('user');
            if (stored) user = JSON.parse(stored);
        } catch (e) {
            console.error("Error parsing user data", e);
        }
    }

    const userName = user?.nombre || user?.nombre_completo || user?.username || "Usuario";
    const roleName = user?.roles?.[0]?.nombre || user?.role || user?.nivel_acceso || "Invitado";
    const avatarInitial = (userName.charAt(0) || "U").toUpperCase();
    const userDivision = user?.division?.nombre?.toLowerCase() || 'secplan';
    const userRoles = user?.roles || [];
    const userRole = userRoles.length > 0 ? userRoles[0].nombre.toLowerCase() : 'admin_general';
    const isLicitacion = window.location.pathname.includes('/licitaciones/');
    let dashLink = isLicitacion
        ? '/ALGARROBO_BASE/frontend/division/licitaciones/admin_proyectos/dashboard.html'
        : `/ALGARROBO_BASE/frontend/division/${userDivision}/${userRole}/dashboard.html`;

    if (user?.nivel_acceso == 10 && !isLicitacion) dashLink = '/ALGARROBO_BASE/frontend/administracion/index.html';

    container.innerHTML = `
    <header class="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50 transition-all duration-300 font-['Outfit']">
        <div class="px-6 py-3">
            <div class="flex justify-between items-center">

                <div class="flex items-center gap-4">
                    <a href="${dashLink}" class="group flex items-center gap-3">
                        <div class="relative w-10 h-10">
                            <div class="absolute inset-0 bg-blue-600 rounded-xl rotate-3 group-hover:rotate-6 transition-transform opacity-20"></div>
                            <div class="absolute inset-0 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl shadow-lg flex items-center justify-center text-white transform group-hover:-translate-y-0.5 transition-all duration-300">
                                <i class="fas fa-water text-lg"></i>
                            </div>
                        </div>
                        <div class="hidden md:block">
                            <h1 class="text-xl font-bold text-gray-800 tracking-tight leading-none group-hover:text-blue-700 transition-colors">Geoportal</h1>
                            <p class="text-[10px] font-bold text-gray-400 tracking-widest uppercase mt-0.5">Municipalidad de Algarrobo</p>
                        </div>
                    </a>
                </div>

                <div class="flex items-center gap-3 md:gap-6">

                    <button onclick="toggleNotifications()" class="relative p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200 group">
                        <i class="fas fa-bell text-xl"></i>
                        <span class="absolute top-2 right-2 w-2.5 h-2.5 bg-red-500 border-2 border-white rounded-full group-hover:scale-110 transition-transform"></span>
                    </button>

                    <div class="h-8 w-px bg-gray-200 hidden md:block"></div>

                    <div class="relative">
                        <button onclick="toggleUserMenu()" class="flex items-center gap-3 p-1 pl-3 pr-2 rounded-full hover:bg-gray-100/80 border border-transparent hover:border-gray-200 transition-all duration-200 group">
                            <div class="text-right hidden md:block">
                                <p class="text-sm font-bold text-gray-700 leading-tight group-hover:text-blue-700 transition-colors">${userName}</p>
                                <p class="text-xs text-gray-500 font-medium">${roleName}</p>
                            </div>
                            <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 p-0.5 shadow-md shadow-blue-500/20 group-hover:shadow-blue-500/40 transition-shadow">
                                <div class="w-full h-full rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center text-white font-bold border-2 border-white/20">
                                    ${avatarInitial}
                                </div>
                            </div>
                            <i class="fas fa-chevron-down text-xs text-gray-400 mr-2 group-hover:mt-1 transition-all"></i>
                        </button>

                        <div id="userMenu" class="hidden absolute right-0 mt-4 w-72 bg-white rounded-2xl shadow-2xl ring-1 ring-black/5 py-2 origin-top-right transform transition-all duration-200 z-50">

                            <div class="px-6 py-4 bg-gradient-to-r from-gray-50 to-white border-b border-gray-100">
                                <p class="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">Cuenta Activa</p>
                                <div class="flex items-center gap-3 mt-3">
                                    <div class="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center text-xl font-bold text-gray-600">
                                        ${avatarInitial}
                                    </div>
                                    <div class="overflow-hidden">
                                        <p class="font-bold text-gray-900 truncate">${userName}</p>
                                        <p class="text-sm text-gray-500 truncate">${roleName}</p>
                                    </div>
                                </div>
                            </div>



                            <a href="#" onclick="logout()" class="group flex items-center gap-4 px-6 py-3 text-red-600 hover:bg-red-50 hover:text-red-700 transition-colors">
                                <span class="w-8 h-8 rounded-lg bg-red-50 group-hover:bg-red-100 flex items-center justify-center transition-colors">
                                    <i class="fas fa-sign-out-alt"></i>
                                </span>
                                <span class="font-medium">Cerrar Sesión</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </header>
    `;
}

function renderSidebar(containerId = "sidebarContainer") {
    const container = document.getElementById(containerId);
    if (!container) return;

    let user = typeof userData !== 'undefined' ? userData : null;
    if (!user) {
        try {
            const stored = localStorage.getItem('userData');
            if (stored) user = JSON.parse(stored);
        } catch (e) { }
    }

    const nivelAcceso = user?.nivel_acceso;
    const currentPath = window.location.pathname.split("/").pop();
    const userDivision = user?.division?.nombre?.toLowerCase() || 'secplan';
    const userRoles = user?.roles || [];
    const userRole = userRoles.length > 0 ? userRoles[0].nombre.toLowerCase() : 'admin_general';
    const baseDir = `/ALGARROBO_BASE/frontend/division/${userDivision}/${userRole}/`;

    const pages = {
        dashboard: baseDir + "dashboard.html",
        proyecto: baseDir + "proyecto.html",
        mapa: baseDir + "mapa.html",
        informe: baseDir + "informe.html",
        calendario: baseDir + "calendario.html",
        documento: baseDir + "documento.html",
        chat: baseDir + "chat.html",
        geomapas: baseDir + "geomapas.html",
        hitos: baseDir + "hitos.html",
        observacion: baseDir + "observacion.html",
        vecinos: baseDir + "vecinos.html",
        informe_dinamico: baseDir + "informe_dinamico.html",
        mapa2: baseDir + "mapa2.html",
        licitaciones: "/ALGARROBO_BASE/frontend/division/licitaciones/admin_proyectos/dashboard.html"
    };

    const linkClasses = (file) => {
        const path = window.location.pathname;
        const isMatch = path.includes(file);
        return isMatch
            ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
            : "text-gray-600 hover:bg-gray-100 hover:text-gray-900 shadow-none";
    };

    const isLicitacionModule = window.location.pathname.includes('/licitaciones/');

    if (isLicitacionModule) {
        const licBase = "/ALGARROBO_BASE/frontend/division/licitaciones/admin_proyectos/";
        container.innerHTML = `
        <aside id="sidebar" class="w-72 bg-white border-r border-gray-200 h-screen sticky top-0 hidden lg:block overflow-y-auto font-['Outfit']">
            <nav class="p-4">
                <div class="mb-8 px-3">
                    <p class="text-[10px] font-black text-blue-600 uppercase tracking-widest">Módulo Especializado</p>
                    <h2 class="text-xl font-bold text-gray-800">Licitaciones</h2>
                </div>

                <ul class="space-y-1">
                    <li>
                        <a href="${licBase}dashboard.html" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses('dashboard.html')}">
                            <i class="fas fa-file-invoice-dollar w-5 text-center"></i>
                            <span class="font-medium">Procesos Activos</span>
                        </a>
                    </li>
                    <li>
                        <a href="${licBase}documentos.html" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses('documentos.html')}">
                            <i class="fas fa-folder-open w-5 text-center"></i>
                            <span class="font-medium">Biblioteca de Bases</span>
                        </a>
                    </li>
                    <li>
                        <a href="${licBase}pasos.html" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses('pasos.html')}">
                            <i class="fas fa-list-check w-5 text-center"></i>
                            <span class="font-medium">Mantenedor de Pasos</span>
                        </a>
                    </li>
                    <li>
                        <a href="${licBase}calendario.html" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses('calendario.html')}">
                            <i class="fas fa-calendar-alt w-5 text-center"></i>
                            <span class="font-medium">Hitos de Apertura</span>
                        </a>
                    </li>
                </ul>

                <div class="mt-10 pt-6 border-t border-gray-100">
                    <p class="px-3 text-[10px] font-medium text-gray-400 uppercase">Sistema de Licitaciones v1.0</p>
                </div>
            </nav>
        </aside>`;
        return;
    }

    const modulosHTML = nivelAcceso === 10 ? `
        <li class="pt-6 mt-4 border-t border-gray-100">
            <p class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4 px-3">Módulos</p>
            <ul class="space-y-1">
                <li>
                    <a href="#" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 text-gray-600 hover:bg-gray-100">
                        <i class="fas fa-road w-5 text-center"></i>
                        <span>Vialidad</span>
                    </a>
                </li>
                <li>
                    <a href="#" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 text-gray-600 hover:bg-gray-100">
                        <i class="fas fa-tint w-5 text-center"></i>
                        <span>Saneamiento</span>
                    </a>
                </li>
                <li>
                    <a href="#" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 text-gray-600 hover:bg-gray-100">
                        <i class="fas fa-tree w-5 text-center"></i>
                        <span>Espacios Públicos</span>
                    </a>
                </li>
            </ul>
        </li>
    ` : "";

    container.innerHTML = `
    <aside id="sidebar" class="w-72 bg-white border-r border-gray-200 h-screen sticky top-0 hidden lg:block overflow-y-auto font-['Outfit']">
        <nav class="p-4">
            <p class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4 px-3 pt-2">Menu Principal</p>
            <ul class="space-y-1">
                <li>
                    <a href="/ALGARROBO_BASE/frontend/division/${userDivision}/${userRole}/dashboard.html" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses('dashboard.html')}">
                        <i class="fas fa-gauge-high w-5 text-center"></i>
                        <span class="font-medium">Dashboard</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.proyecto}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.proyecto)}">
                        <i class="fas fa-diagram-project w-5 text-center"></i>
                        <span class="font-medium">Proyectos</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.documento}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.documento)}">
                        <i class="fas fa-file-lines w-5 text-center"></i>
                        <span class="font-medium">Documentos</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.geomapas}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.geomapas)}">
                        <i class="fas fa-layer-group w-5 text-center"></i>
                        <span class="font-medium">GeoMapas</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.observacion}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.observacion)}">
                        <i class="fas fa-layer-group w-5 text-center"></i>
                        <span class="font-medium">Observaciones</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.hitos}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.hitos)}">
                        <i class="fas fa-flag-checkered w-5 text-center"></i>
                        <span class="font-medium">Hitos</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.mapa}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.mapa)}">
                        <i class="fas fa-map-location-dot w-5 text-center"></i>
                        <span class="font-medium">Mapa</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.mapa2}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.mapa2)}">
                        <i class="fas fa-map w-5 text-center"></i>
                        <span class="font-medium">Mapa 2</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.informe}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.informe)}">
                        <i class="fas fa-chart-line w-5 text-center"></i>
                        <span class="font-medium">Informes</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.informe_dinamico}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.informe_dinamico)}">
                        <i class="fas fa-chart-pie w-5 text-center"></i>
                        <span class="font-medium">Informe Dinámico</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.calendario}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.calendario)}">
                        <i class="fas fa-calendar-days w-5 text-center"></i>
                        <span class="font-medium">Calendario</span>
                    </a>
                </li>
                <li>
                     <a href="/ALGARROBO_BASE/frontend/geoportal/index.html" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 text-gray-600 hover:bg-gray-100 hover:text-gray-900">
                         <i class="fas fa-globe-americas w-5 text-center"></i>
                         <span class="font-medium">Geoportal</span>
                     </a>
                </li>

                <li class="pt-4">
                    <p class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 px-3">Herramientas</p>
                </li>
                <li>
                    <a href="${pages.chat}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.chat)}">
                        <i class="fas fa-comments w-5 text-center"></i>
                        <span>ChatBot IA</span>
                    </a>
                </li>
                <li>
                    <a href="${pages.vecinos}" class="flex items-center space-x-3 p-3 rounded-xl transition-all duration-200 ${linkClasses(pages.vecinos)}">
                        <i class="fas fa-users w-5 text-center"></i>
                        <span class="font-medium">App Vecinos</span>
                    </a>
                </li>
            </ul>

            <ul class="space-y-1">
                ${modulosHTML}
            </ul>
        </nav>
    </aside>
    `;
}

function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-5 right-5 z-[9999] space-y-3';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    const colors = {
        success: 'border-emerald-500 text-emerald-700 bg-emerald-50',
        error: 'border-red-500 text-red-700 bg-red-50',
        warning: 'border-amber-500 text-amber-700 bg-amber-50',
        info: 'border-blue-500 text-blue-700 bg-blue-50'
    };

    toast.className = `flex items-center gap-3 px-4 py-3 rounded-xl border-l-4 shadow-xl translate-x-full transition-transform duration-300 ${colors[type] || colors.info}`;
    toast.innerHTML = `
        <i class="fas ${icons[type] || icons.info} text-lg"></i>
        <p class="font-bold text-sm text-gray-800">${message}</p>
    `;

    container.appendChild(toast);

    setTimeout(() => toast.style.transform = 'translateX(0)', 10);

    setTimeout(() => {
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function toggleUserMenu() {
    var menu = document.getElementById('userMenu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

function toggleNotifications() {
    console.log('Notificaciones clicked');
}

function logout() {
    localStorage.removeItem('userData');
    localStorage.removeItem('user_data');
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    window.location.href = '/ALGARROBO_BASE/frontend/index.html';
}

document.addEventListener('click', function (e) {
    var userMenu = document.getElementById('userMenu');
    if (userMenu && !e.target.closest('#userMenu') && !e.target.closest('[onclick*="toggleUserMenu"]')) {
        userMenu.classList.add('hidden');
    }
});

renderHeader("headerRender")
renderSidebar("asideRender")
