# ServiceFlow

Prototipo académico del curso Diseño de Software (2026-2): sistema web para coordinar
reparaciones y repuestos de Samsung Perú. Datos ficticios; no se conecta con Samsung.

El front copia el diseño final (`Design.html`) y el back sigue el informe:
arquitectura por capas `Vista → Facade → Service → Repository → DAO → Base de datos`.

## Base de datos: MySQL (XAMPP)

Los datos se guardan en MySQL, en la base **`serviceflow`** (servidor `127.0.0.1:3306`,
usuario `root` sin contraseña, el de XAMPP). Antes de encender la app:

1. Abre el **XAMPP Control Panel** y pulsa **Start** en **MySQL**.
2. Para ver los datos, en **MySQL Workbench** abre tu conexión `root@127.0.0.1:3306` y
   elige el esquema `serviceflow`. Las tablas empiezan con el nombre del módulo:
   `ordenes_ordenreparacion`, `inventario_inventario`, `core_aviso`, `core_bitacora`, etc.

Si el root tiene contraseña, antes de encender la app escribe en cmd `set DB_PASSWORD=tu_clave`.
Para usar SQLite sin servidor: `set DB_ENGINE=sqlite`.

## Cómo encenderlo (cmd)

```
cd C:\Users\erick\diseñosamsung
.venv\Scripts\activate
python manage.py runserver
```

Abre http://127.0.0.1:8000/. Para apagarlo: `Ctrl + C`.

### Primera vez en otra computadora

Con MySQL encendido, crea la base (en Workbench:
`CREATE DATABASE serviceflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`) y luego:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_demo
```

### Volver los datos al inicio (antes de la sustentación)

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo --reiniciar
```

## Usuarios de prueba (contraseña de todos: `demo1234`)

| Usuario | Persona | Rol | Centro | Dónde entra |
|---|---|---|---|---|
| `aquispe` | Álvaro Quispe | Cliente | — | Inicio |
| `jtolentino` | Junior Tolentino | Cliente | — | Inicio |
| `amoreno` | Alessandro Moreno | Técnico | Miraflores | Acceso del personal → Técnica |
| `lramos` | Lucía Ramos | Técnica | San Isidro | Acceso del personal → Técnica |
| `ebaigorrea` | Erick Baigorrea | Almacén | Miraflores | Acceso del personal → Almacén |
| `scaycho` | Santiago Caycho | Coordinador | Los dos | Acceso del personal → Coordinación |
| `admin` | Administrador | — | — | Acceso del personal → Administración (o `/admin`) |

Órdenes de ejemplo, como en el diseño: RO-00001 Recibida, RO-00002 y RO-00003 En espera de
repuesto, RO-00004 En reparación (entrega en 3 días), RO-00005 Entregada en San Isidro.

## Recorrido de la demo (orden RO-00002: necesita 2 pantallas y Miraflores tiene 1)

1. `aquispe` → Mis reparaciones: RO-00002 "Esperando un repuesto", sin fecha.
2. `ebaigorrea` → Reservas: aviso de falta de stock → **Pedir traslado desde San Isidro**.
3. `scaycho` → Solicitudes → **Aprobar traslado**. Reportes muestra el faltante.
4. `ebaigorrea` → Registrar ingreso → **Registrar traslado**; luego en Reservas, **Reservar**.
5. `amoreno` → Órdenes → RO-00002 → **Confirmar fecha** y **Marcar reparada**.
6. `aquispe` → RO-00002 aparece "Lista para recoger", con fecha e historial.
7. `admin` → `/admin` → Bitácora: cada paso quedó registrado con su usuario.

Los avisos al cliente (RF-06) aparecen en **Avisos** (con el número de avisos sin leer en
el menú), en el detalle de cada reparación y, además, como correo en la ventana del servidor.

## Pruebas

```
python manage.py test core
```

Con MySQL corren las 42, incluida la de dos reservas a la vez por la última unidad
(sección 2.7). Las pruebas usan una base aparte, `test_serviceflow`, y la borran al terminar.

## Dónde está cada cosa

| Capa / patrón | Archivos |
|---|---|
| Vistas (MVC) | `atencion/views.py`, `ordenes/views.py`, `inventario/views.py`, `coordinacion/views.py` |
| Facade | `core/facade.py` (`ServicioPosventaFacade`) |
| Service | `ordenes/services.py`, `inventario/services.py`, `coordinacion/services.py`, `core/avisos.py` |
| DTO | `*/dtos.py` (`SeguimientoDTO`, `ResultadoReservaDTO`, `SolicitudPendienteDTO`…) |
| Repository | `*/repositories.py` |
| DAO | `*/daos.py` (`InventarioDAO.buscar_con_bloqueo` hace el `SELECT … FOR UPDATE`) |
| Singleton | `core/configuracion.py` (`ConfiguracionSistema`) |
| Adapter | `inventario/fuentes.py` (`FuenteInventario`, `InventarioExternoAdapter`) |
| Plantillas y estilos | `templates/`, `static/css/app.css` |
