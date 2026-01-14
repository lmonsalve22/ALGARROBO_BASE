
const BASE = "/ALGARROBO_BASE";

const diccionarioRutas = {
    10: [
        `${BASE}/frontend/division/secplan/admin_general/dashboard.html`,
        `${BASE}/frontend/division/secplan/admin_general/proyecto.html`,
        `${BASE}/frontend/division/secplan/admin_general/mapa.html`,
        `${BASE}/frontend/division/secplan/admin_general/informe.html`,
        `${BASE}/frontend/division/secplan/admin_general/calendario.html`,
        `${BASE}/frontend/administracion/index.html`
    ],
    11: [
        `${BASE}/frontend/division/secplan/admin_proyectos/dashboard.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/proyecto.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/mapa.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/informe.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/calendario.html`
    ],
    12: [
        `${BASE}/frontend/division/secplan/director_obras/dashboard.html`,
        `${BASE}/frontend/division/secplan/director_obras/proyecto.html`,
        `${BASE}/frontend/division/secplan/director_obras/mapa.html`,
        `${BASE}/frontend/division/secplan/director_obras/informe.html`,
        `${BASE}/frontend/division/secplan/director_obras/calendario.html`
    ]
};

function verificarRutaPermitida(user) {
    if (!user) return false;
    const nivelAcceso = user.nivel_acceso;
    const path = window.location.pathname;

    const rutasPermitidas = diccionarioRutas[nivelAcceso] || [];
    const pathNormalizado = path.replace(/\/+$/, "");

    return rutasPermitidas.some(ruta =>
        pathNormalizado.includes(ruta.replace(/\/+$/, ""))
    );
}

function checkLoginStatus() {
    const userDataString = localStorage.getItem('userData') || localStorage.getItem('user_data');
    if (!userDataString) {
        window.location.href = `${BASE}/frontend/index.html`;
        return [null, null];
    }

    const userData = JSON.parse(userDataString);
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    const token = localStorage.getItem('authToken');

    if (!isLoggedIn || isLoggedIn !== 'true' || !token) {
        window.location.href = `${BASE}/frontend/index.html`;
        return [null, null];
    }

    return [token, userData];
}

function logout() {
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    localStorage.removeItem('user_data');
    localStorage.removeItem('user');
    window.location.href = `${BASE}/frontend/index.html`;
}

function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    if (menu) menu.classList.toggle('hidden');
}

function toggleNotifications() {
    console.log("Notificaciones - En desarrollo");
}

const [token, userData] = checkLoginStatus();

document.addEventListener('click', function (event) {
    const userMenu = document.getElementById('userMenu');
    const userButton = event.target.closest('button[onclick="toggleUserMenu()"]');

    if (userMenu && !userButton && !userMenu.contains(event.target)) {
        userMenu.classList.add('hidden');
    }
});


function strToBytes(str) {
    return new TextEncoder().encode(str);
}

function bytesToStr(bytes) {
    return new TextDecoder().decode(bytes);
}

function getKey(seed) {
    const OFUSCADO = "VgAMFkZXBBFdUEpXQwFFXRZXA19NXV1XXQdQBVpDFlBIIwMkGxUkEgJcIRAXAUBcBQ=="; // <-- generado antes

    const data = Uint8Array.from(
        atob(OFUSCADO),
        c => c.charCodeAt(0)
    );

    const s = strToBytes(seed);
    const out = new Uint8Array(data.length);

    for (let i = 0; i < data.length; i++) {
        out[i] = data[i] ^ s[i % s.length];
    }

    return bytesToStr(out);
}





