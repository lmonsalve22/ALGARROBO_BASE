
// Función para verificar el estado de login
const BASE = "/ALGARROBO_BASE"
//const BASE = ""
const diccionarioRutas = {
    10: [`${BASE}/frontend/division/secplan/admin_general/dashboard.html`,
        `${BASE}/frontend/division/secplan/admin_general/proyecto.html`,
        `${BASE}/frontend/division/secplan/admin_general/mapa.html`,
        `${BASE}/frontend/division/secplan/admin_general/informe.html`,
        `${BASE}/frontend/division/secplan/admin_general/calendario.html`
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
    if (!isLoggedIn || isLoggedIn !== 'true' || !verificarRutaPermitida(userData)) {
        // Redirigir a la página de login si no está logueado
        window.location.href = '../../index.html';
    }
    const token = localStorage.getItem('authToken'); // trae el string
    return [token,userData];
}
 
const salida = checkLoginStatus(); 
const token = salida[0]
const userData = salida[1]
console.log(token,userData)
