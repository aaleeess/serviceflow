"""Íconos de trazo del diseño final (inline SVG, sin emojis) y filtros de presentación."""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

TRAZOS = {
    "marca": '<path d="M4 7h10a3 3 0 0 1 0 6H8a3 3 0 0 0 0 6h12"></path><circle cx="20" cy="19" r="1.2"></circle>',
    "maletin": '<rect x="3" y="7" width="18" height="13" rx="2"></rect><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>',
    "mas": '<path d="M12 5v14"></path><path d="M5 12h14"></path>',
    "pulso": '<path d="M3 12h4l3-8 4 16 3-8h4"></path>',
    "campana": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10.3 21a2 2 0 0 0 3.4 0"></path>',
    "usuario": '<circle cx="12" cy="8" r="4"></circle><path d="M4 21c0-4 4-6 8-6s8 2 8 6"></path>',
    "candado": '<rect x="5" y="11" width="14" height="10" rx="2"></rect><path d="M8 11V8a4 4 0 0 1 8 0v3"></path>',
    "ojo": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"></path><circle cx="12" cy="12" r="3"></circle>',
    "alerta": '<circle cx="12" cy="12" r="9"></circle><path d="M12 8v5"></path><path d="M12 16h.01"></path>',
    "triangulo": '<path d="M12 9v4"></path><path d="M12 17h.01"></path><path d="M10.3 3.9L2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"></path>',
    "check": '<path d="M5 12l5 5 9-10"></path>',
    "reloj": '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path>',
    "llave": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4 2.5-2.5z"></path>',
    "caja": '<path d="M21 8l-9-5-9 5 9 5 9-5z"></path><path d="M3 8v8l9 5 9-5V8"></path><path d="M12 13v8"></path>',
    "aprobar": '<path d="M9 11l3 3 8-8"></path><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"></path>',
    "escudo": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"></path>',
    "cuadros": '<rect x="3" y="3" width="7" height="7" rx="1.5"></rect><rect x="14" y="3" width="7" height="7" rx="1.5"></rect><rect x="3" y="14" width="7" height="7" rx="1.5"></rect><rect x="14" y="14" width="7" height="7" rx="1.5"></rect>',
    "flechas": '<path d="M7 4v16"></path><path d="M3 8l4-4 4 4"></path><path d="M17 20V4"></path><path d="M13 16l4 4 4-4"></path>',
    "barras": '<path d="M4 20V10"></path><path d="M10 20V4"></path><path d="M16 20v-7"></path><path d="M22 20H2"></path>',
    "prohibido": '<circle cx="12" cy="12" r="9"></circle><path d="M5.6 5.6l12.8 12.8"></path>',
    "salir": '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4"></path><path d="M10 16l4-4-4-4"></path><path d="M14 12H4"></path>',
    "buscar": '<circle cx="11" cy="11" r="7"></circle><path d="M20 20l-4-4"></path>',
    "flecha": '<path d="M4 12h15"></path><path d="M13 6l6 6-6 6"></path>',
    "info": '<circle cx="12" cy="12" r="9"></circle><path d="M12 11v5"></path><path d="M12 8h.01"></path>',
    "pin": '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"></path><circle cx="12" cy="10" r="2.5"></circle>',
}


@register.simple_tag
def icono(nombre, tam=18, grosor=2, color="currentColor"):
    return format_html(
        '<svg aria-hidden="true" width="{0}" height="{0}" viewBox="0 0 24 24" fill="none" stroke="{1}" '
        'stroke-width="{2}" stroke-linecap="round" stroke-linejoin="round">{3}</svg>',
        tam, color, grosor, mark_safe(TRAZOS.get(nombre, "")),
    )


@register.filter
def iniciales(nombre):
    partes = [p for p in str(nombre).split() if p]
    return "".join(p[0] for p in partes[:2]).upper() or "?"


@register.filter
def cuando(fecha):
    """'Hoy 10:42', 'Ayer 18:05' o '24/11 09:58', en hora de Lima."""
    from datetime import timedelta

    from django.utils import timezone

    if not fecha:
        return ""
    local = timezone.localtime(fecha)
    hoy = timezone.localdate()
    if local.date() == hoy:
        return f"Hoy {local:%H:%M}"
    if local.date() == hoy - timedelta(days=1):
        return f"Ayer {local:%H:%M}"
    return f"{local:%d/%m %H:%M}"


@register.filter
def inicial_minuscula(texto):
    texto = str(texto)
    return texto[:1].lower() + texto[1:]


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]


@register.filter
def dia_mes(fecha):
    """'27 nov'."""
    return f"{fecha.day} {MESES[fecha.month - 1]}" if fecha else ""


@register.filter
def clase_estado(estado):
    """Color de la píldora de cada estado interno."""
    return {
        "RECIBIDA": "azul", "EN_EVALUACION": "azul", "EN_ESPERA_REPUESTO": "ambar",
        "EN_REPARACION": "verde", "REPARADA": "verde", "ENTREGADA": "gris", "CANCELADA": "rojo",
    }.get(estado, "gris")
