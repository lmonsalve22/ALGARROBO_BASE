
// Función para verificar el estado de login
function checkLoginStatus() {
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    console.log(isLoggedIn)
    
    if (!isLoggedIn || isLoggedIn !== 'true') {
        // Redirigir a la página de login si no está logueado
        window.location.href = '../../index.html';
    }
    
}
checkLoginStatus() 
const userDataString = localStorage.getItem('userData'); // trae el string
const userData = JSON.parse(userDataString); // lo convierte a objeto
const token = localStorage.getItem('authToken'); // trae el string
console.log(userData,userData)
