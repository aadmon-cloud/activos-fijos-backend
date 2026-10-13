# Guía: ingreso con Google

El sistema solo permite ingresar con la cuenta de Google, y solo a **personas que el administrador ya registró**. Nadie
se crea solo al ingresar.

## Cómo funciona (en corto)
1. La persona pulsa **Ingresar con Google**; el navegador va a Google y ella elige su cuenta.
2. Google la devuelve a `/login/google` con un token de identidad firmado.
3. El backend valida el token (firma, que sea para esta aplicación, que el correo esté verificado por Google, que tenga
   menos de 5 minutos y que corresponda a ese intento de ingreso) y busca un usuario **activo** con ese correo.
4. Si existe, abre la sesión (cookie `HttpOnly`); si no, responde que la cuenta no tiene acceso.

No se carga ningún script de terceros ni hay secretos en el navegador: el ID de cliente es público.

## 1. Crear el ID de cliente (una sola vez)
En [Google Cloud Console](https://console.cloud.google.com/):
1. Elige (o crea) el proyecto de la fundación.
2. **APIs y servicios → Pantalla de consentimiento de OAuth.** Tipo **Interno** si la cuenta es de Google Workspace
   (solo entran cuentas de la organización); si no, **Externo**. Pon el nombre de la aplicación y un correo de soporte.
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**:
   - Tipo de aplicación: **Aplicación web**.
   - **Orígenes de JavaScript autorizados:** `http://localhost:3000` (y, en producción, la dirección pública, p. ej.
     `https://activos.ejemplo.org`).
   - **URI de redireccionamiento autorizados:** `http://localhost:3000/login/google` (y, en producción,
     `https://activos.ejemplo.org/login/google`). Debe coincidir **exactamente**, incluida la ruta.
4. Copia el **ID de cliente** (termina en `.apps.googleusercontent.com`). El «secreto» que muestra Google **no se usa**.

## 2. Configurar
- Backend (`BACKEND/.env`): `GOOGLE_CLIENT_ID=<el ID de cliente>`
- Frontend (`.env.local`): `NEXT_PUBLIC_GOOGLE_CLIENT_ID=<el mismo ID>`
- Reinicia los dos servidores (el frontend lee la variable al arrancar).

## 3. Registrar al primer administrador
Como el ingreso exige un usuario ya registrado, el primero se crea desde la terminal (en `BACKEND`):

```
python -m scripts.crear_administrador --email persona@fundacionmarialuisa.org --nombre Ana --apellido Perez
```

Usa el correo exacto de su cuenta de Google. Si ya existe, lo reactiva y le devuelve el rol de administrador general.
Después, ese administrador crea a los demás desde **Usuarios** (con el correo de Google de cada persona).

## Errores frecuentes
| Síntoma | Causa |
|---|---|
| Google muestra «redirect_uri_mismatch» | El URI de redireccionamiento no está registrado, o difiere (http/https, puerto, ruta) |
| «El ingreso con Google no está configurado» | Falta `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (o no se reinició el frontend) o `GOOGLE_CLIENT_ID` en el backend |
| «Esta cuenta de Google no tiene acceso» | El correo no está registrado, o el usuario está desactivado |
| «No se pudo validar el ingreso con Google» | El ID de cliente del backend no coincide con el del frontend, o el token tardó más de 5 minutos |

## Contraseñas
Ya no existen para los usuarios: al registrar a alguien no se pide contraseña y el ingreso con correo y contraseña está
deshabilitado (`403 USR-012`). `LOGIN_PASSWORD_HABILITADO=true` lo reabre y **solo** debe usarse en el equipo local para
pruebas automatizadas; en producción debe quedar en `false`.
