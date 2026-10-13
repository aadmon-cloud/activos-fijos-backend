# Guia: correo (Gmail) y recordatorios automaticos

Que configurar para que el sistema envie correos reales y recuerde las devoluciones y los proximos mantenimientos cada dia.

## 1. Correo de salida (Gmail)

El sistema envia por SMTP. Con Gmail:

1. Usa una cuenta dedicada (p. ej. `sistema@tu-dominio.org`). La cuenta debe tener la **verificacion en dos pasos** activa.
2. Crea una **contrasena de aplicacion** (Cuenta de Google → Seguridad → Contrasenas de aplicaciones). Es la que se usa
   como `SMTP_PASSWORD`; la contrasena normal de la cuenta no sirve.
3. Variables del servicio:

| Variable | Valor |
| --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USE_TLS` | `true` |
| `SMTP_USER` | La cuenta de Gmail |
| `SMTP_FROM_EMAIL` | La misma cuenta (Gmail reescribe otros remitentes) |
| `SMTP_FROM_NAME` | `Sistema de Activos Fijos` |
| `SMTP_PASSWORD` | **Solo en local** (`.env`) |
| `SMTP_PASSWORD_SECRET_NAME` | **Fuera de local**: nombre del secreto en Secret Manager que guarda la contrasena |
| `APP_URL` | Direccion publica del frontend, sin barra final (para los enlaces de los correos) |

Fuera de local la contrasena **no** va en variables de entorno: guardala en Secret Manager y dale el rol
`Secret Manager Secret Accessor` a la cuenta de servicio de Cloud Run.

```bash
printf '%s' 'LA-CONTRASENA-DE-APLICACION' | gcloud secrets create smtp-password --data-file=-
gcloud secrets add-iam-policy-binding smtp-password \
  --member="serviceAccount:CUENTA-DE-CLOUD-RUN" --role="roles/secretmanager.secretAccessor"
```

Limites de Gmail: unos 500 destinatarios al dia en una cuenta personal y unos 2000 en Google Workspace. Un correo con varios
destinatarios cuenta por cada uno.

Para comprobarlo: entra como administrador a **Notificaciones**; arriba dice si el correo esta configurado. Un aviso que no
se pudo enviar aparece como *fallida* con el motivo y se puede **reenviar**.

## 2. Recordatorios diarios (Cloud Scheduler)

El endpoint `POST /api/notificaciones/procesar-recordatorios` recuerda las devoluciones y avisa de los proximos
mantenimientos. Cloud Scheduler lo llama una vez al dia con un token de identidad de Google; no hay contrasena que guardar.

```bash
PROYECTO=tu-proyecto
REGION=us-central1
SERVICIO=activos-fijos-backend
URL=$(gcloud run services describe $SERVICIO --region $REGION --format='value(status.url)')

# 1) Cuenta de servicio del planificador
gcloud iam service-accounts create activos-planificador --display-name="Planificador de recordatorios"
CUENTA="activos-planificador@${PROYECTO}.iam.gserviceaccount.com"

# 2) Si el servicio de Cloud Run exige autenticacion, permitirle invocarlo
gcloud run services add-iam-policy-binding $SERVICIO --region $REGION \
  --member="serviceAccount:${CUENTA}" --role="roles/run.invoker"

# 3) Decirle al backend que cuenta es la autorizada y cual es su audiencia
gcloud run services update $SERVICIO --region $REGION \
  --update-env-vars "SCHEDULER_SERVICE_ACCOUNT_EMAIL=${CUENTA},GOOGLE_CLOUD_RUN_AUDIENCE=${URL}"

# 4) El job diario (7:00 hora de Bogota)
gcloud scheduler jobs create http recordatorios-activos \
  --location=$REGION --schedule="0 7 * * *" --time-zone="America/Bogota" \
  --uri="${URL}/api/notificaciones/procesar-recordatorios" --http-method=POST \
  --oidc-service-account-email="${CUENTA}" --oidc-token-audience="${URL}"
```

Probar sin esperar: `gcloud scheduler jobs run recordatorios-activos --location=$REGION`, o el boton **Procesar
recordatorios** de la pantalla Notificaciones.

Detalles que conviene saber:

- La audiencia del token debe ser **exactamente** `GOOGLE_CLOUD_RUN_AUDIENCE` (la URL del servicio, sin barra final).
- El backend solo acepta el token si el correo es el de `SCHEDULER_SERVICE_ACCOUNT_EMAIL`. Otra cuenta, aunque su token sea
  valido, recibe 401/403.
- Cada recordatorio de devolucion se envia **una sola vez** por movimiento; el job puede correr todos los dias sin repetir.
- Si una de las dos tareas falla, la otra se ejecuta igual y el error aparece en `errores` de la respuesta.
