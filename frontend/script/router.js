
// Función para verificar el estado de login
const BASE = "/ALGARROBO_BASE"
//const BASE = ""
const diccionarioRutas = {
    10: [`${BASE}/frontend/division/secplan/admin_general/dashboard.html`,
        `${BASE}/frontend/division/secplan/admin_general/proyecto.html`,
        `${BASE}/frontend/division/secplan/admin_general/mapa.html`,
        `${BASE}/frontend/division/secplan/admin_general/informe.html`,
        `${BASE}/frontend/division/secplan/admin_general/calendario.html`
    ],
    11: [`${BASE}/frontend/division/secplan/admin_proyectos/dashboard.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/proyecto.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/mapa.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/informe.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/calendario.html`
    ],
    12: [`${BASE}/frontend/division/secplan/director_obras/dashboard.html`,
        `${BASE}/frontend/division/secplan/director_obras/proyecto.html`,
        `${BASE}/frontend/division/secplan/director_obras/mapa.html`,
        `${BASE}/frontend/division/secplan/director_obras/informe.html`,
        `${BASE}/frontend/division/secplan/director_obras/calendario.html`
    ]
};

function verificarRutaPermitida(user) {
    const nivelAcceso = user?.nivel_acceso;
    
    const path = window.location.pathname;

    // Si no existe el nivel de acceso en el diccionario, no permitir
    const rutasPermitidas = diccionarioRutas[nivelAcceso] || [];

    // Normalizar eliminando posibles slashes finales
    const pathNormalizado = path.replace(/\/+$/, "");

    return rutasPermitidas.some(ruta => 
        ruta.replace(/\/+$/, "") === pathNormalizado
    );
}

function checkLoginStatus() {
    const userDataString = localStorage.getItem('userData'); // trae el string
    const userData = JSON.parse(userDataString); // lo convierte a objeto

    const isLoggedIn = localStorage.getItem('isLoggedIn');    
     if (!isLoggedIn || isLoggedIn !== 'true') {
        // Redirigir a la página de login si no está logueado
        window.location.href = `${BASE}/frontend/index.html`;
        //console.log("aka salio");
    }

    
    if (!isLoggedIn || isLoggedIn !== 'true' || !verificarRutaPermitida(userData)) {
        // Redirigir a la página de login si no está logueado
        //window.location.href = `${BASE}/frontend/index.html`;
        console.log("aka salio");
    }
    const token = localStorage.getItem('authToken'); // trae el string
    return [token,userData];
}

// Función para logout
        function logout() {
            // Eliminar la sesión del usuario
            localStorage.removeItem('isLoggedIn');
            localStorage.removeItem('userRole');            
            // Redirigir a la página de login
            window.location.href = `${BASE}/frontend/index.html`;
        }

// User menu
function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    menu.classList.toggle('hidden');
}
 
const salida = checkLoginStatus(); 
const token = salida[0]
const userData = salida[1]
console.log(token,userData)
