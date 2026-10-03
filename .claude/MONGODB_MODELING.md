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
    id_persona: str
    nombre: str       # desnormalizado para evitar lookup en lectura
    fecha: datetime
```

**Por qué `nombre` embebido:** permite mostrar "Creado por Ana García el 12/06/2026" sin join. El nombre puede quedar desactualizado si la persona lo cambia — aceptable para auditoría.

---

## Embeber vs referenciar

### Embeber cuando:
- El subdocumento **siempre se lee junto al padre**
- El array **tiene límite razonable**
- El dato es **propiedad exclusiva** del documento padre
- Necesitas **atomicidad** en escritura

### Referenciar cuando:
- El dato **existe y se consulta independientemente**
- El dato es **compartido** por varios documentos
- El array puede crecer **sin límite previsible**
- La entidad referenciada **cambia con frecuencia**

### Regla general para desnormalizar valores de otra colección

Embeber el valor (además del ID) cuando se cumplen **las tres condiciones**:

| Condición | Ejemplo que la cumple | Ejemplo que NO la cumple |
|---|---|---|
| Se muestra en **listados frecuentes** | Nombre del ponente en lista de eventos | Dirección completa del sitio |
| **Cambia raramente** | Nombre de un rol, nombre de un país | Precio de un producto, saldo de cuenta |
| **La desactualización es aceptable** | Nombre del curso en un registro histórico | Estado actual de un contrato |

Si las tres se cumplen → embeber `{id, nombre}`. Si alguna falla → solo guardar el ID.

---

## Tipos de identificadores

| Tipo | bsonType | Cuándo usarlo |
|---|---|---|
| `_id` | objectId | Siempre, identificador técnico de Mongo |
| Consecutivos de negocio | string / int | Cuando existe un código visible al usuario |

---

## Cuándo un array embebido se convierte en colección propia

Separar en colección cuando se cumpla **al menos uno**:

| Criterio | Ejemplo |
|---|---|
| El array puede crecer **sin límite previsible** | Historial muy activo |
| Los items se consultan **independientemente del padre** | "Dame todos los X del sitio Y este mes" |
| Cada item es un **documento sustancial** por sí solo | Entidad con su propio historial |
| Se necesitan **índices propios** sobre los items | `(id_padre, fecha)` no tiene sentido embebido |

**Señal práctica:** si te encuentras escribiendo un pipeline con `$unwind` para consultar los items del array con frecuencia, probablemente debería ser una colección separada.

## Señales de alerta

- Array embebido que podría tener **cientos de items** → evaluar colección separada
- **Lookup frecuente** de un campo que se muestra siempre → desnormalizar
- Filtro frecuente sobre un campo **sin índice** → agregar índice
- Documento que **supera los 16MB** (límite de Mongo) → rediseñar

---

## Checklist antes de proponer el modelo

- [ ] Identifiqué el identificador técnico y el natural (si existe)
- [ ] Todos los campos obligatorios están definidos
- [ ] `creado_por` y `actualizado_por` incluidos si aplica auditoría
- [ ] Si tiene estados: definí las transiciones válidas y decidí si necesita historial
- [ ] Decidí explícitamente qué se embebe y qué se referencia (y por qué)
- [ ] Identifiqué las consultas principales y propuse índices para cada una
- [ ] Revisé si algún array puede crecer sin límite
