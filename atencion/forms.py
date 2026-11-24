from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SolicitudForm(forms.Form):
    """Formulario de nueva solicitud (CU-02, Figura 5). La validación final la hace el servicio."""

    modelo_equipo = forms.CharField(label="Modelo del equipo", max_length=100,
                                    error_messages={"required": "Escribe el modelo de tu equipo."})
    falla_reportada = forms.CharField(label="¿Qué le pasa?", widget=forms.Textarea(attrs={"rows": 4}),
                                      error_messages={"required": "Cuéntanos qué falla tiene el equipo."})
    centro = forms.ChoiceField(label="Centro de servicio",
                               error_messages={"required": "Elige el centro donde dejarás tu equipo."})

    def __init__(self, *args, centros=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["centro"].choices = [("", "Elige un centro")] + [(c.id, f"{c.nombre} · {c.horario_atencion}")
                                                                     for c in centros]


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)
    email = forms.EmailField(label="Correo", help_text="Aquí te llegan los avisos de tu reparación.")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")
