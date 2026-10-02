# MongoDB — Modelado de colecciones

Usar este archivo cuando el usuario describe un requerimiento o historia de usuario y necesita diseñar una colección nueva.

---

## Proceso antes de escribir código

1. Identificar la entidad principal y su límite de dominio
2. Definir campos obligatorios vs opcionales desde el día uno
3. Decidir qué se embebe y qué se referencia
4. Identificar si necesita estado → historial
5. Definir las consultas principales → índices
6. Evaluar si algún array puede crecer sin límite
7. Definir el identificador natural (si existe)

---

## Patrón de auditoría — `creado_por` / `actualizado_por`

**Siempre** en lugar de `created_at` / `updated_at` / `created_by_id`.

```python
class AuditPersona(BaseDomainEntity):
    id_persona: str   # ObjectId como string
    nombre: str       # desnormalizado para evitar lookup en lectura
    fecha: datetime
```

Validator:
```python
"creado_por": {
    "bsonType": "object",
    "required": ["id_persona", "nombre", "fecha"],
    "properties": {
        "id_persona": {"bsonType": "objectId"},
        "nombre": {"bsonType": "string"},
        "fecha": {"bsonType": "date"},
    },
},
"actualizado_por": { ... mismo esquema ... }
```

**Por qué `nombre` embebido:** permite mostrar "Creado por Ana García el 12/06/2026" sin join. El nombre puede quedar desactualizado si la persona lo cambia — esto es aceptable para auditoría; refleja el nombre en el momento de la acción.

---

## Patrón de historial de estados

Usar cuando la entidad tiene una **máquina de estados** y se necesita trazabilidad de quién cambió qué y cuándo.

```python
class HistorialEstado(BaseDomainEntity):
    estado_anterior: str | None = None   # None en la creación inicial
    estado_nuevo: str
    fecha: datetime
    cambiado_por: CambiadoPor            # {persona_id, nombre}
    observacion: str | None = None
```

```python
# En el validator
"historial_estados": {
    "bsonType": "array",
    "items": {
        "required": ["estado_nuevo", "fecha", "cambiado_por"],
        "properties": {
            "estado_anterior": {"bsonType": "string"},
            "estado_nuevo": {"bsonType": "string"},
            "fecha": {"bsonType": "date"},
            "cambiado_por": {
                "bsonType": "object",
                "required": ["persona_id", "nombre"],
                "properties": {
                    "persona_id": {"bsonType": "objectId"},
                    "nombre": {"bsonType": "string"},
                },
            },
            "observacion": {"bsonType": "string"},
        },
    },
},
```

**Cuándo usar historial embebido vs colección separada:**

| Situación | Decisión |
|---|---|
| Pocos estados posibles, transiciones poco frecuentes | Array embebido en el documento |
| Muchas transiciones por documento (decenas/mes) | Colección separada `historial_<entidad>` |
| Solo importa el estado actual, no el historial | Sin historial, solo `estado` + `actualizado_por` |

---

## Embeber vs referenciar

### Embeber cuando:
- El subdocumento **siempre se lee junto al padre** (no tiene sentido sin él)
- El array **tiene límite razonable** (clases de un curso, items de un pedido)
- El dato es **propiedad exclusiva** del documento padre
- Necesitas **atomicidad** en escritura (actualizar padre e hijo en una operación)

### Referenciar cuando:
- El dato **existe y se consulta independientemente**
- El dato es **compartido** por varios documentos
- El array puede crecer **sin límite previsible**
- La entidad referenciada **cambia con frecuencia** (el nombre actualizado debe verse en todos lados)

### Desnormalización parcial (patrón del proyecto)

Cuando se referencia una entidad, embeber también el `nombre` para lectura rápida:

```python
# En lugar de solo el ID:
id_persona: str

# Usamos:
class ItemConPersona:
    id_persona: str   # para consultas y joins cuando sea necesario
    nombre: str       # para mostrar sin lookup
```

**Cuándo aplicar:** cuando el campo se muestra frecuentemente en listados y un lookup sería costoso. El tradeoff es que el nombre puede quedar desactualizado — aceptable para datos históricos, cuestionable para datos operativos activos.

### Regla general para desnormalizar valores de otra colección

Embeber el valor (además del ID) cuando se cumplen **las tres condiciones**:

| Condición | Ejemplo que la cumple | Ejemplo que NO la cumple |
|---|---|---|
| Se muestra en **listados frecuentes** (sin que valga la pena un lookup) | Nombre del autor en lista de artículos | Dirección completa del sitio |
| **Cambia raramente** (pocas veces al año o nunca) | Nombre de un rol, nombre de un país | Precio de un producto, saldo de cuenta |
| **La desactualización es aceptable** (dato de contexto, no de decisión) | Nombre del recurso en un registro histórico | Estado actual de un contrato |

Si las tres se cumplen → embeber `{id, nombre}` (o el campo relevante).  
Si alguna falla → solo guardar el ID y hacer lookup cuando se necesite.

---

## Tipos de identificadores

| Tipo | bsonType | Cuándo usarlo |
|---|---|---|
| `_id` | objectId | Siempre, identificador técnico de Mongo |
| IDs de entidades propias | objectId | Entidades del sistema |
| IDs de sistemas legados enteros | int | Cuando el sistema origen usa enteros |
| Consecutivos de negocio | string / int | Cuando existe un código visible al usuario |

---

## Preguntas clave al modelar

**Sobre el dominio:**
- ¿Qué campos son obligatorios desde el día uno?
- ¿Existe un identificador natural del negocio (código, número de documento, correo)?
- ¿Tiene estados? ¿Cuáles son las transiciones válidas? ¿Necesita historial?
- ¿Qué datos de auditoría necesita? (siempre `creado_por` + `actualizado_por`)

**Sobre las relaciones:**
- ¿Qué entidades referencia? ¿Se leen siempre juntas o por separado?
- ¿Alguna relación puede crecer mucho (muchos items por documento)?
- ¿Qué datos del relacionado conviene desnormalizar para lectura?

**Sobre las consultas:**
- ¿Cuál es el listado principal? ¿Por qué campos filtra? ¿Cómo ordena?
- ¿Hay filtros secundarios frecuentes (por estado, fecha, usuario)?
- ¿Hay combinaciones de filtros que se repiten juntas? → índice compuesto
- ¿El listado puede devolver muchos documentos? → paginación obligatoria

**Sobre el crecimiento:**
- ¿Algún array puede crecer sin límite? (historial muy activo, comentarios, eventos)
- ¿Cuántos documentos se esperan en un año? ¿En tres años?
- ¿Hay datos históricos que se consultan poco pero deben conservarse?

---

## Cuándo un array embebido se convierte en colección propia

Separar en colección cuando se cumpla **al menos uno**:

| Criterio | Ejemplo |
|---|---|
| El array puede crecer **sin límite previsible** | Sesiones de asistencia de una entidad activa por años |
| Los items se consultan **independientemente del padre** | "Dame todos los registros del tipo X este mes" |
| Cada item es un **documento sustancial** por sí solo (varios campos, su propio historial) | Entidad con muchos campos propios |
| Se necesitan **índices propios** sobre los items | `(id_padre, fecha)` no tiene sentido en un array embebido |
| Varios documentos distintos pueden **"tener"** ese mismo tipo de item | Estructura reutilizable entre módulos |

Mantener embebido cuando:
- El array tiene un tope natural bajo (raramente más de 50 items)
- Los items no tienen sentido fuera del padre
- Nunca se consultan por separado

**Señal práctica:** si te encuentras escribiendo un pipeline con `$unwind` para consultar los items del array con frecuencia, probablemente debería ser una colección separada.

## Señales de alerta

- Array embebido que podría tener **cientos de items** → evaluar colección separada
- **Lookup frecuente** de un campo que se muestra siempre → desnormalizar
- Filtro frecuente sobre un campo **sin índice** → agregar índice
- Documento que **supera los 16MB** (límite de Mongo) → rediseñar
- `$lookup` en cada consulta del listado principal → evaluar desnormalización
- Actualización que toca **miles de documentos** por un cambio en el relacionado → revisar si conviene referenciar menos

---

## Checklist antes de proponer el modelo

- [ ] Identifiqué el identificador técnico y el natural (si existe)
- [ ] Todos los campos obligatorios están definidos
- [ ] `creado_por` y `actualizado_por` incluidos con el patrón `AuditPersona`
- [ ] Si tiene estados: definí las transiciones válidas y decidí si necesita historial
- [ ] Decidí explícitamente qué se embebe y qué se referencia (y por qué)
- [ ] Identifiqué las consultas principales y propuse índices para cada una
- [ ] Revisé si algún array puede crecer sin límite
- [ ] Si hay desnormalización parcial: documenté qué campo se desnormaliza y por qué
- [ ] El modelo fue pensado visualmente antes de escribir código
